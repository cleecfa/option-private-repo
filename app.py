import os
from tda import auth, client
import pandas as pd
import json
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from selenium import webdriver
from datetime import datetime
from datetime import timedelta
import pytz
from streamlit_autorefresh import st_autorefresh


now = datetime.now(pytz.UTC) - timedelta(hours=8)
mkt_open = datetime.strptime(datetime.strftime(now, "%Y-%m-%d"), "%Y-%m-%d") + timedelta(hours=6, minutes=30)
mkt_close = datetime.strptime(datetime.strftime(now, "%Y-%m-%d"), "%Y-%m-%d") + timedelta(hours=13, minutes=30)
current_time = datetime.strptime(datetime.strftime(now, "%Y-%m-%d %H:%M"), "%Y-%m-%d %H:%M")
now = str(now.strftime("%Y-%m-%d %H:%M") + " PST")

############## Streamlit Containers ##################
header = st.container()
dataset = st.container()
interactive = st.container()

#Initial placeholder prior to getting user inputs
symbol = 'SPY'


### Environment Variables ###
token_path = os.environ.get("token_path")
api_key = os.environ.get("api_key")
redirect_uri = os.environ.get("redirect_uri")


### Need this driver for deploying on Heroku ###
### Using Heroku Config Variables ###
chrome_options = webdriver.ChromeOptions()
chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)

try:
    c = auth.client_from_token_file(token_path, api_key)
except FileNotFoundError:
    from selenium import webdriver
    with driver:
        c = auth.client_from_login_flow(
            driver, api_key, redirect_uri, token_path)


#Auto Refresher
st_autorefresh(interval=1 * 60 * 1000, key="dataframerefresh")
# while True:
#     if current_time > mkt_open and current_time < mkt_close:
#         st_autorefresh(interval=0.75 * 60 * 1000, key="dataframerefresh")
#     else:
#         continue


## Get underlying price ###
def create_underlying_df():

    r = c.get_quotes(symbol)
    assert r.status_code == 200, "status code:" + str(
        r.status_code) + ".. Failed getting underlying. Most likely TD Authentication Issue"

    underlying = r.json()[symbol]
    underlying_df = pd.json_normalize(underlying)

    return underlying_df


def create_equity_option_df():

    r = c.get_option_chain(
        symbol,
        contract_type=c.Options.ContractType.ALL)
    assert r.status_code == 200, "status code:" + str(
        r.status_code) + ".. Failed getting options. Most likely TD Authentication Issue"

    ### Get options data and turn it into a DF ###
    equity_option_list = []

    calls = r.json()['callExpDateMap']
    for exp in calls:
        for strike in calls[exp]:
            for call in calls[exp][strike]:
                equity_option_list.append(call)

    puts = r.json()['putExpDateMap']
    for exp in puts:
        for strike in puts[exp]:
            for put in puts[exp][strike]:
                equity_option_list.append(put)

    equity_option_df = pd.json_normalize(equity_option_list)

    # Dataset Filter (Not UI filter)
    filtered_equity_option_list = filter_equity_option(equity_option_df)

    # Call transform_equity_option_df(df, prefix) function
    df = transform_equity_option_df(filtered_equity_option_list)

    return df


def transform_equity_option_df(df):
    cols_to_drop = ['exchangeName', 'bid', 'ask', 'last', 'bidSize', 'bidAskSize', 'askSize', 'highPrice', 'lastSize',
                    'lowPrice', 'openPrice',
                    'closePrice', 'tradeDate', 'tradeTimeInLong', 'netChange', 'optionDeliverablesList',
                    'settlementType',
                    'deliverableNote', 'markChange', 'nonStandard', 'pennyPilot', 'mini',
                    'nonStandard']  # cols to be dropped

    cols_to_date = ['expirationDate']  # cols to convert to date
    cols_to_datetime = []  # cols to convert to datetime

    # 1. Remove cols
    df.drop(cols_to_drop, axis=1, inplace=True)

    # 2. Convert to Datetime or Date
    for col in cols_to_date:
        df[col] = df[col].apply(pd.to_datetime, unit='ms')
        df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')

    for col in cols_to_datetime:
        df[col] = df[col].apply(pd.to_datetime, unit='ms')
        df[col] = pd.to_datetime(df[col]).dt.strftime('%B %d, %Y, %r')

    return df

    # 3. Parse underlying symbol from option symbol
    # df['underlying_symbol'] = df['symbol'].str.split('_').str[0]


def filter_equity_option(df):
    # 4. Initial Filters for zeros and NaN
    df = df[(df['strikePrice'] != 'NaN') & (df['gamma'] != 'NaN')]

    return df


def apply_user_filter(df):
    df = df[(pd.to_datetime(df['expirationDate']) >= expiration_date_slider[0]) &
            (pd.to_datetime(df['expirationDate']) <= expiration_date_slider[1])]

    return df


def create_aggregate_table(df, base_activity_type):
    # Create directional gamma col
    # print(df.dtypes)
    df.loc[df['putCall'] == 'PUT', 'directional_gamma'] = df['gamma'] * -1
    df.loc[df['putCall'] == 'CALL', 'directional_gamma'] = df['gamma']

    # Calculate gamma & delta Notional

    df['notional_gamma'] = df[base_activity_type] * df['directional_gamma'] * underlying_price * 100
    df['notional_delta'] = df[base_activity_type] * df['delta'] * underlying_price * 100

    # Make strikePrice a dimension
    df['strikePrice'] = df['strikePrice'].apply(str)

    # Aggregate by option type AND sp  --> pre-grouped to be used in the chart
    df_by_all = df.groupby(by=['putCall', 'strikePrice'], as_index=False).agg(
        {'notional_gamma': 'sum', 'notional_delta': 'sum'})
    df_by_all = df_by_all.rename(columns={'notional_gamma': 'ng_by_all', 'notional_delta': 'nd_by_all'})

    # Aggregate by sp only  --> pre-grouped to be used in the chart
    df_by_sp = df.groupby(by=['strikePrice'], as_index=False).agg({'notional_gamma': 'sum', 'notional_delta': 'sum'})
    df_by_sp = df_by_sp.rename(columns={'notional_gamma': 'ng_by_sp', 'notional_delta': 'nd_by_sp'})

    # Highest NG by sp  --> max to be used in the chart
    df_max_gamma = df_by_sp[df_by_sp.ng_by_sp == df_by_sp.ng_by_sp.max()]
    df_max_gamma = df_max_gamma.rename(columns={'ng_by_sp': 'max_ng'})

    df_max_delta = df_by_sp[df_by_sp.nd_by_sp == df_by_sp.nd_by_sp.max()]
    df_max_delta = df_max_delta.rename(columns={'nd_by_sp': 'max_nd'})

    # Lowest NG by sp  --> min to be used in the chart
    df_min_gamma = df_by_sp[df_by_sp.ng_by_sp == df_by_sp.ng_by_sp.min()]
    df_min_gamma = df_min_gamma.rename(columns={'ng_by_sp': 'min_ng'})

    df_min_delta = df_by_sp[df_by_sp.nd_by_sp == df_by_sp.nd_by_sp.min()]
    df_min_delta = df_min_delta.rename(columns={'nd_by_sp': 'min_nd'})

    # Merge all tables
    df_merged = pd.merge(df_by_all, df_by_sp, how='left', on=['strikePrice'])
    df_merged = pd.merge(df_merged, df_max_gamma, how='left', on=['strikePrice'])
    df_merged = pd.merge(df_merged, df_min_gamma, how='left', on=['strikePrice'])
    df_merged = pd.merge(df_merged, df_max_delta, how='left', on=['strikePrice'])
    df_merged = pd.merge(df_merged, df_min_delta, how='left', on=['strikePrice'])

    # df_merged.drop(['putCall', 'strikePrice', 'ng_by_all', 'nd_by_all', 'max_ng', 'max_nd', 'min_nd', 'min_nd','ng_by_sp','nd_by_sp'], axis=1, inplace=True)
    # df_merged = df_merged.rename(columns={'ng_by_sp_x': 'ng_by_sp', 'nd_by_sp_x': 'nd_by_sp', 'min_ng_x': 'min_ng'})
    # df_merged = df_merged[['putCall','strikePrice','ng_by_all','nd_by_all','max_ng','max_nd','min_nd','min_nd']]

    df_aggregated = df_merged

    return df_aggregated


########### Streamlit CSS Adjustments ############
# CSS for header area padding - top margin
st.write('<style>div.block-container{padding-top:3rem;}</style>', unsafe_allow_html=True)
# CSS for header area padding - middle margin
st.write('<style>hr{margin: 0em 0px;)</style>', unsafe_allow_html=True)
st.write('<style>div.css-1n76uvr{gap: 1rem;}</style>', unsafe_allow_html=True)
# CSS for side bar padding - top margin
st.write('<style>div.css-1vq4p4l{padding: 1rem 1rem 1rem;}</style>', unsafe_allow_html=True)
# Metrics - reduce the font size
st.write('<style>div.css-1xarl3l{font-size: 1.5rem}</style>', unsafe_allow_html=True)
# Slide Title - left padding
st.write('<style>div.css-10y5sf6 {padding-left: 73px;}</style>', unsafe_allow_html=True)
# Slide Element colors
st.write('''<style>div.st-cr {
    background: linear-gradient(to right, red 0%, red 100%, 
    red 100%, red 100%, red 100%, red 100%);
}</style>''', unsafe_allow_html=True)

st.write('''<style>div.css-10y5sf6 {
    color: red;
}</style>''', unsafe_allow_html=True)
st.write('''<style>div.css-demzbm {
    background-color: white;
}</style>''', unsafe_allow_html=True)

# Hide "Made with Streamlit"
# hide_streamlit_style = """
#             <style>
#             #MainMenu {visibility: hidden;}
#             footer {visibility: hidden;}
#             </style>
#             """
# st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Menu Color to Red
st.write('<style>button.css-1rs6os{background-color: red !important;}</style>', unsafe_allow_html=True)

########### Streamlit Containers ###########
with header:
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("Mikook Option Analytics")

    with col2:
        st.markdown(
            f'<h6 style="color:white;font-size:10px; text-align:left;position: bottom;right: 0;">{"Refreshed as of  " + now}</h6>',
            unsafe_allow_html=True)

    st.markdown("""---""")

with dataset:  # streamlit container

    with st.sidebar:
        # User Input - Ticker
        symbol = st.text_input('Enter an Underlying Ticker:', 'SPY')
        if symbol:
            symbol = symbol.strip().upper()

        base_activity_type = st.radio(
            "Select a base activity type assumption",
            ('Open Interest', 'Volume'))
        if base_activity_type == "Open Interest":
            base_activity_type = "openInterest"
        elif base_activity_type == "Volume":
            base_activity_type = "totalVolume"
        else:
            pass

    clean_df = create_equity_option_df()

    # Expiration Date Multiselect
    with st.sidebar:

        exp_date_list = clean_df['expirationDate'].unique().tolist()

        # Important: Remove current expiration if past option market close at 1:30PM
        today = datetime.today()
        # st.write(today)
        current_expiration = datetime.strptime(min(exp_date_list), "%Y-%m-%d") + timedelta(hours=13, minutes=15)
        # st.write(current_expiration)
        if today > current_expiration:
            exp_date_list.remove(min(exp_date_list))
        else:
            pass

        start = datetime.strptime(min(exp_date_list), '%Y-%m-%d')  # str to datetime
        end = datetime.strptime(max(exp_date_list), '%Y-%m-%d')
        value = (start, end)

        expiration_date_slider = st.slider('Select Expiration Dates:', value=value)

    user_filtered_clean_df = apply_user_filter(clean_df)
    # print(user_filtered_clean_df.dtypes)

    underlying_df = create_underlying_df()
    underlying_price = float(underlying_df['lastPrice'])

    final_aggregated_table = create_aggregate_table(user_filtered_clean_df, base_activity_type)

    col_a, col_b, col_c, col_d, col_e, col_f = st.columns(6, gap="small")

    df_col_selected_metrics = user_filtered_clean_df[
        ['putCall', 'expirationDate', 'strikePrice', 'totalVolume', 'openInterest',
         'volatility', 'delta', 'gamma', 'theta', 'rho', 'theoreticalOptionValue']]

    # Underlying
    underlying_price = round(underlying_price, 2)
    with col_a:
        st.metric(label="Underlying Ticker", value=symbol)

    with col_b:
        st.metric(label="Underlying Price", value=underlying_price)

    # Put/Call Ratio
    pc_df_col_selected_by_vol = df_col_selected_metrics.groupby(by=['putCall'], as_index=False).agg(
        {'totalVolume': 'sum'})
    pc_df_col_selected_by_oi = df_col_selected_metrics.groupby(by=['putCall'], as_index=False).agg(
        {'openInterest': 'sum'})

    if df_col_selected_metrics.empty == False:
        # Volume P/C Ratio
        vol_pc_ratio = round(
            (pc_df_col_selected_by_vol['totalVolume'].loc[pc_df_col_selected_by_vol['putCall'] == 'PUT'].values / \
             pc_df_col_selected_by_vol['totalVolume'].loc[pc_df_col_selected_by_vol['putCall'] == 'CALL'].values)[0], 1)

        # Open Interest P/C Ratio
        OI_pc_ratio = round(
            (pc_df_col_selected_by_oi['openInterest'].loc[pc_df_col_selected_by_oi['putCall'] == 'PUT'].values / \
             pc_df_col_selected_by_oi['openInterest'].loc[pc_df_col_selected_by_oi['putCall'] == 'CALL'].values)[0],
            1)

        # Net Notional Delta Calc
        df_col_selected_metrics['total_delta'] = df_col_selected_metrics['delta'] * \
                                                 df_col_selected_metrics['openInterest'] * underlying_price * 100
        net_delta = df_col_selected_metrics['total_delta'].sum()
        if abs(net_delta) >= 1000000000:
            net_delta = str(round(df_col_selected_metrics['total_delta'].sum() / 1000000000, 1)) + "B"

        elif abs(net_delta) >= 1000000:
            net_delta = str(round(df_col_selected_metrics['total_delta'].sum() / 1000000, 1)) + "M"

        else:
            net_delta = str(round(df_col_selected_metrics['total_delta'].sum() / 1000, 1)) + "K"

        # Calculate Summary Metrics
        user_filtered_clean_df['total_gamma'] = user_filtered_clean_df['directional_gamma'] * \
                                                user_filtered_clean_df[base_activity_type] * underlying_price * 100
        net_gamma = user_filtered_clean_df['total_gamma'].sum()

        if abs(net_gamma) >= 1000000000:
            net_gamma = str(round(net_gamma / 1000000000, 1)) + "B"

        elif abs(net_gamma) >= 1000000:
            net_gamma = str(round(net_gamma / 1000000, 1)) + "M"

        else:
            net_gamma = str(round(net_gamma / 1000, 1)) + "K"

        df_col_selected_for_detailed_table = df_col_selected_metrics

    else:
        vol_pc_ratio = 0
        OI_pc_ratio = 0
        net_delta = 0
        net_gamma = 0

    with col_c:
        st.metric(label="Notional Delta", value=net_delta)

    with col_d:
        st.metric(label="Notional Gamma", value=net_gamma)

    with col_e:
        st.metric(label='Volume P/C', value=vol_pc_ratio)

    with col_f:
        st.metric(label='OI P/C', value=OI_pc_ratio)

    ##########################################  Explanation ###########################################
    strike_price_at_lowest_gamma = final_aggregated_table['strikePrice'].loc[
        final_aggregated_table['ng_by_sp_x'] == final_aggregated_table['min_ng']].unique()[0]

    strike_price_at_highest_gamma = final_aggregated_table['strikePrice'].loc[
        final_aggregated_table['ng_by_sp_x'] == final_aggregated_table['max_ng']].unique()[0]

    expander = st.expander("What the data says about " + symbol)
    expander.write(f"""
                    This analysis for *****:blue[{symbol}]***** option is based on *****:blue[{base_activity_type}]***** 
                    with expiration dates from *****:blue[{expiration_date_slider[0].strftime('%m/%d/%Y')}]*****
                    to *****:blue[{expiration_date_slider[1].strftime('%m/%d/%Y')}]***** as of *****{now}*****.
                    """)
    if '-' in net_gamma:
        expander.write(f"""
                            {net_gamma} **:red[ Negative]** net gamma: If it stays in the negative net gamma territory, 
                            we may see **:red[Price Movements in wider range]** than usual.  
                            """)

        if '-' in net_delta:
            expander.write(f"""
                            {net_delta} **:red[ Negative]** net delta: holding other things constant, some 
                            **:red[Downward Pressure]** can be anticipated.
                                """)
            if float(strike_price_at_lowest_gamma) < underlying_price:
                expander.write(f""" 
                                    Next immediate support level: **:red[{strike_price_at_lowest_gamma}]**
                                    """)

    else:
        expander.write(f"""
                            Based on {net_gamma} **:green[ Positive]** net gamma on {symbol}, if it stays in the positive net gamma territory, 
                            relatively **:green[Stable Price Movement]** can be anticipated.
                            """)
        if '-' not in net_delta:
            expander.write(f"""
                               **:green[ Positive]** net delta, {net_delta} implies that buy-side is likely overall 
                               long on the market at this moment. That means market makers are likely to be 
                                on the short call and their delta-hedging activities can add some **:green[Upward Momentum]**. 

                                Watch out for large near-term calls as their maturities could cause some cancellation of market maker's delta hedging.  
                                """)
            if float(strike_price_at_highest_gamma) > underlying_price:
                expander.write(f""" 
                                    Next immediate resistance level: **:green[{strike_price_at_highest_gamma}]**
                                    """)

        else:
            expander.write(f"""
                               **:red[ Negative]** net delta, {net_delta} implies that buy-side is likely overall 
                               short on the market at this moment. That means market makers are likely to be 
                                on the long call and their delta-hedging activities can add some **:red[Downward Pressure]**. 

                                Watch out for large near-term calls as their maturities could cause some cancellation of market maker's delta hedging.  
                                """)

            if float(strike_price_at_lowest_gamma) < underlying_price:
                expander.write(f""" 
                                    Next immediate support level: **:red[{strike_price_at_lowest_gamma}]**
                                    """)

    #######################################################################################
    # Chart1 - Bar Chart: NG by option type and sp
    # px.bar doc: https://plotly.com/python-api-reference/generated/plotly.express.bar.html
    fig1 = px.bar(
        final_aggregated_table,
        x='strikePrice',
        y='ng_by_all',
        color='putCall',
        # height=600,
        # width=800,
        color_discrete_map={'CALL': 'Green', 'PUT': 'red'},
        opacity=0.85,
        title='Notional Option Gamma')

    fig1.update_layout(
        autosize=True,
        width=700,
        height=700)

    # Update mode
    fig1.update_layout(modebar_remove=['zoom', 'pan', 'select', 'autoScale', 'resetScale', 'lasso2d'])

    # View Range Filter
    view_adjuster_bottom = underlying_price - (underlying_price ** 0.7)
    view_adjuster_top = underlying_price + (underlying_price ** 0.7)
    fig1.update_layout(yaxis_range=[final_aggregated_table['min_ng'], 4])
    fig1.update_layout(xaxis_range=[view_adjuster_bottom, view_adjuster_top])
    fig1.update_layout(dragmode=False)

    # Axe Titles
    fig1.update_yaxes(ticklabelposition="inside top", title='Gamma Notional Exposure ($)')
    fig1.update_xaxes(ticklabelposition="inside bottom", title='Strike Price')

    fig1.update_layout(legend=dict(
        title="",
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))
    # Vertical reference line: underlying price
    fig1.add_vline(x=underlying_price, line_width=3, line_dash="dash", line_color="grey",
                   annotation_text="Underlying Price", annotation_position="top")

    # Chart2 - Scatter Chart: Max NG
    fig2 = px.scatter(
        final_aggregated_table,
        x='strikePrice',
        y='max_ng',
        render_mode='svg',
        text="max_ng")

    # Annotation
    fig2.update_traces(text=' Highest Net Gamma')
    fig2.update_traces(textposition='middle right')
    fig2.update_traces(marker=dict(size=10, symbol="diamond", color='Green',
                                   line=dict(width=2,
                                             color='White')),
                       selector=dict(mode='markers+text'))

    # Chart3 - Scatter Chart: Min NG
    fig3 = px.scatter(
        final_aggregated_table,
        x='strikePrice',
        y='min_ng',
        render_mode='svg',
        text='min_ng')

    # Annotation
    fig3.update_traces(text=' Lowest Net Gamma')
    fig3.update_traces(textposition='middle right')
    fig3.update_traces(marker=dict(size=10, symbol="diamond", color='Red',
                                   line=dict(width=2,
                                             color='White')),
                       selector=dict(mode='markers+text'))

    # Chart3 - Area Chart: Net Gamma Notional Value
    fig4 = px.area(
        final_aggregated_table,
        x='strikePrice',
        y='ng_by_sp_x', color_discrete_sequence=['White'])

    # Create legend #
    fig4['data'][0]['showlegend'] = True
    fig4['data'][0]['name'] = 'Gamma Notional'

    # Combine all Figs into a single chart object and show in the container
    all_fig = go.Figure(data=fig1.data + fig2.data + fig3.data + fig4.data, layout=fig1.layout)
    st.plotly_chart(all_fig)

    ################################################################################################################################

    fig_a = px.bar(
        final_aggregated_table,
        x='strikePrice',
        y='nd_by_all',
        color='putCall',
        # height=600,
        # width=800,
        color_discrete_map={'CALL': 'Green', 'PUT': 'red'},
        opacity=0.85,
        title='Notional Option Delta')

    # Update mode
    fig_a.update_layout(modebar_remove=['zoom', 'pan', 'select', 'autoScale', 'resetScale', 'lasso2d'])

    fig_a.update_layout(
        autosize=True,
        width=700,
        height=700)

    # View Range Filter
    view_adjuster_bottom = underlying_price - (underlying_price ** 0.6)
    view_adjuster_top = underlying_price + (underlying_price ** 0.6)
    fig_a.update_layout(xaxis_range=[view_adjuster_bottom, view_adjuster_top])
    fig_a.update_layout(dragmode=False)

    # Axe Titles
    fig_a.update_yaxes(ticklabelposition="inside top", title='Delta Notional Exposure ($)')
    fig_a.update_xaxes(ticklabelposition="inside bottom", title='Strike Price')
    fig_a.update_layout(legend=dict(
        title="",
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))
    # Vertical reference line: underlying price
    fig_a.add_vline(x=underlying_price, line_width=2, line_dash="dash", line_color="grey",
                    annotation_text="Underlying Price", annotation_position="top")

    # Chart2 - Scatter Chart: Max NG
    fig_b = px.scatter(
        final_aggregated_table,
        x='strikePrice',
        y='max_nd',
        render_mode='svg',
        text="max_nd")

    # Annotation
    fig_b.update_traces(text=' Highest Net Delta')
    fig_b.update_traces(textposition='middle right')
    fig_b.update_traces(marker=dict(size=10, symbol="diamond", color='Green',
                                    line=dict(width=2,
                                              color='White')),
                        selector=dict(mode='markers+text'))

    # Chart3 - Scatter Chart: Min NG
    fig_c = px.scatter(
        final_aggregated_table,
        x='strikePrice',
        y='min_nd',
        render_mode='svg',
        text='min_ng')

    # Annotation
    fig_c.update_traces(text=' Lowest Net Delta')
    fig_c.update_traces(textposition='middle right')
    fig_c.update_traces(marker=dict(size=10, symbol="diamond", color='Red',
                                    line=dict(width=2,
                                              color='White')),
                        selector=dict(mode='markers+text'))

    # Chart3 - Area Chart: Net Gamma Notional Value
    fig_d = px.area(
        final_aggregated_table,
        x='strikePrice',
        y='nd_by_sp_x', color_discrete_sequence=['White'])

    # Create legend #
    fig_d['data'][0]['showlegend'] = True
    fig_d['data'][0]['name'] = 'Delta Notional'

    # Combine all Figs into a single chart object and show in the container
    all_fig = go.Figure(data=fig_a.data + fig_b.data + fig_c.data + fig_d.data, layout=fig_a.layout)
    st.plotly_chart(all_fig)

    ###########################################################################################################################

    # Detailed Table View
    user_filtered_clean_df = user_filtered_clean_df[
        ['putCall', 'expirationDate', 'mark', 'theoreticalOptionValue', 'strikePrice']]
    user_filtered_clean_df['Valuation'] = user_filtered_clean_df['theoreticalOptionValue'] - user_filtered_clean_df[
        'mark']
    df_call = user_filtered_clean_df[(user_filtered_clean_df['putCall'] != 'call')].set_index(['expirationDate'])
    df_put = user_filtered_clean_df[(user_filtered_clean_df['putCall'] != 'put')].set_index(['expirationDate'])
    df_theo = df_call.merge(df_put, on=['expirationDate', 'strikePrice'], suffixes=('_call', '_put'))

    df_theo = df_theo[(df_theo['putCall_call'] == "CALL") & (df_theo['putCall_put'] == "PUT")]
    # Rename Cols
    df_theo = df_theo.rename(columns={'mark_call': 'Call Prem',
                                      'theoreticalOptionValue_call': 'Call Theo Value',
                                      'mark_put': 'Put Prem',
                                      'theoreticalOptionValue_put': 'Put Theo Value',
                                      'Valuation_call': 'Call Discount',
                                      'Valuation_put': 'Put Discount'})

    st.markdown('**Thoretical Value  VS.  Premium**')
    df_theo = df_theo[
        ['Call Prem', 'Call Theo Value', 'Call Discount', 'strikePrice', 'Put Prem', 'Put Theo Value', 'Put Discount']]
    st.dataframe(df_theo)
