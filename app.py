from dotenv import load_dotenv #For hiding credentials in .env  Doc:https://www.youtube.com/watch?v=YdgIWTYQ69A
import os
from tda import auth, client #Doc:https://tda-api.readthedocs.io/en/v1.3.0/index.html
import pandas as pd
import json
import time
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

start = time.time()
# If first time autheticating, you need to create a token json file.
# To do that, for the token_path variable, pass in a dummy json name with the name you would like the token
# file to be. Then, it will pop out a chrome window for logging into the TD (client side, not the developer side)
# Run with the first uthentiation process

# Credit to: alexgolec/tda-api
# https://github.com/alexgolec/tda-api

load_dotenv() #Create environment variable

### Secure Personal Credentials ###
token_path = os.getenv('token_path') #!!! Important: MUST BE without "r" in the path quotation !!!
api_key= os.getenv('api_key')
redirect_uri = os.getenv('redirect_uri')

### User Inputs ###
symbol = st.text_input('Underlying Ticker:', 'SPY')
if symbol:
    symbol = symbol.strip()
####################

try:
    c = auth.client_from_token_file(token_path, api_key)
except FileNotFoundError:
    from selenium import webdriver
    with webdriver.Chrome() as driver:
        c = auth.client_from_login_flow(
            driver, api_key, redirect_uri, token_path)


r = c.get_option_chain(
    symbol,
    contract_type=c.Options.ContractType.ALL
)
assert r.status_code == 200, r.raise_for_status()


### Get underlying price ###
underlying = c.get_quotes(symbol)
underlying_price = float(json.dumps(underlying.json()[symbol]['lastPrice']))
print(type(underlying_price))


option_list = []

calls = r.json()['callExpDateMap']
for exp in calls:
    for strike in calls[exp]:
        for call in calls[exp][strike]:
            option_list.append(call)

puts = r.json()['putExpDateMap']
for exp in puts:
    for strike in puts[exp]:
        for put in puts[exp][strike]:
            option_list.append(put)


df = pd.json_normalize(option_list)


########## DF Transformation ##########
cols_to_drop = ['exchangeName','bid','ask','last','bidSize','bidAskSize','askSize','highPrice','lastSize','lowPrice', 'openPrice',
                'closePrice','tradeDate','tradeTimeInLong', 'netChange', 'optionDeliverablesList','settlementType',
                'deliverableNote','markChange', 'nonStandard', 'pennyPilot','mini','nonStandard'] # cols to be dropped
cols_to_datetime = ['expirationDate', 'lastTradingDay','quoteTimeInLong']  # cols to convert to datetime

df.drop(cols_to_drop, axis=1, inplace=True)

df[cols_to_datetime] = df[cols_to_datetime].apply(pd.to_datetime, unit='ms')  # convert epoch in millisecond to datetime
for col in cols_to_datetime:  # convert GMT to PDT
    df[col] = df[col].dt.tz_localize("GMT").dt.tz_convert('America/Los_Angeles').dt.tz_localize(None)

print(time.time())

df['underlying_symbol'] = df['symbol'].str.split('_').str[0]  # Get underlying symbol
df['underlying_price'] = df['strikePrice'] + df['intrinsicValue']

df = df[(df['totalVolume'] != 0) | (df['openInterest'] != 0)]
df = df[df['gamma'] != 'NaN']


############## Streamlit ##################
header = st.container()
dataset = st.container()
interactive = st.container()

with header:
    st.title('Option Gamma Notional Exposure')

with dataset:
    gamma_df = df[['putCall','gamma','expirationDate','strikePrice','openInterest']].copy()
    # Update Put gamma
    gamma_df.loc[gamma_df['putCall'] == 'PUT', 'directional_gamma'] = gamma_df['gamma'] * -1
    gamma_df.loc[gamma_df['putCall'] == 'CALL', 'directional_gamma'] = gamma_df['gamma']
    gamma_df['notional_gamma'] = gamma_df['openInterest']*gamma_df['directional_gamma']*underlying_price*100
    # Make strikePrice a dimensional value
    gamma_df['strikePrice'] = gamma_df['strikePrice'].apply(str)


    gamma_df_by_all = gamma_df.groupby(by=['putCall','strikePrice'], as_index=False).agg({'notional_gamma': 'sum'})
    gamma_df_by_all = gamma_df_by_all.rename(columns = {'notional_gamma': 'ng_by_all'})

    gamma_df_by_sp = gamma_df.groupby(by=['strikePrice'], as_index=False).agg({'notional_gamma': 'sum'})
    gamma_df_by_sp = gamma_df_by_sp.rename(columns={'notional_gamma': 'ng_by_sp'})


    gamma_df_max = gamma_df_by_sp[gamma_df_by_sp.ng_by_sp == gamma_df_by_sp.ng_by_sp.max()]
    gamma_df_max = gamma_df_max.rename(columns={'ng_by_sp': 'max_ng'})

    gamma_df_min = gamma_df_by_sp[gamma_df_by_sp.ng_by_sp == gamma_df_by_sp.ng_by_sp.min()]
    gamma_df_min = gamma_df_min.rename(columns={'ng_by_sp': 'min_ng'})

    gamma_df_merged = pd.merge(gamma_df_by_all, gamma_df_by_sp, how='left', on=['strikePrice'])
    gamma_df_merged = pd.merge(gamma_df_merged, gamma_df_max, how='left', on=['strikePrice'])
    gamma_df_merged = pd.merge(gamma_df_merged, gamma_df_min, how='left', on=['strikePrice'])

    # gamma_df_merged = pd.merge(gamma_df_merged, max_ng, how='left')
    # gamma_df_merged['max_ng'] = gamma_df_by_sp['ng_by_sp'].max(axis=0)
    # gamma_df_merged['min_ng'] = gamma_df_by_sp['ng_by_sp'].min(axis=0)
    # gamma_df_merged.to_csv('merged_test.csv')
    # print(gamma_df_merged)

    # gamma_df_merged.to_csv('check_max.csv')
    # print(grouped_gamma_df)

    fig1 = px.bar(
        gamma_df_merged,
        x = 'strikePrice',
        y = 'ng_by_all',
        color = 'putCall',
        # height=600,
        # width=800,
        color_discrete_map={'CALL': 'Green', 'PUT': 'red'},
        opacity=0.85)

    fig1.update_layout(xaxis_range=[underlying_price * 0.8, underlying_price * 1.2])
    fig1.update_yaxes(ticklabelposition="inside top", title='Gamma Notional Exposure ($)')
    fig1.update_xaxes(ticklabelposition="inside top", title='Strike Price')
    fig1.update_layout(legend_title_text='')


    fig2 = px.scatter(
        gamma_df_merged,
        x='strikePrice',
        y='max_ng',
        render_mode='svg',
        text="max_ng")

    fig2.update_traces(text=' Highest NG')
    fig2.update_traces(textposition='middle right')
    fig2.update_traces(marker=dict(size=10,symbol="diamond",color='Green',
                                  line=dict(width=2,
                                            color='DarkSlateGrey')),
                      selector=dict(mode='markers+text'))


    fig3 = px.scatter(
        gamma_df_merged,
        x='strikePrice',
        y='min_ng',
        render_mode='svg',
        text='min_ng')

    fig3.update_traces(text=' Lowest NG')
    fig3.update_traces(textposition='middle right')
    fig3.update_traces(marker=dict(size=10, symbol="diamond", color='Red',
                                   line=dict(width=2,
                                             color='DarkSlateGrey')),
                       selector=dict(mode='markers+text'))

    fig4 = px.area(
        gamma_df_merged,
        x='strikePrice',
        y='ng_by_sp', color_discrete_sequence=['Black'])


    ### To show legend ###
    fig4['data'][0]['showlegend'] = True
    fig4['data'][0]['name'] = 'Gamma Notional'


    all_fig = go.Figure(data=fig1.data + fig2.data + fig3.data + fig4.data, layout=fig1.layout)
    st.plotly_chart(all_fig)



# streamlit run app.py

end = time.time()
time_taken = round(end-start, 2)

print(f"Completed in {time_taken} second")
# print(calls)
