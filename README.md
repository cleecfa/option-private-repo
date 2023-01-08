# Application url
https://option-app-v1.herokuapp.com/

# Description
This is a real-time web application that pulls options quotes, greeks, and underlying asset info based on user parameters (i.e. ticker, expiration dates, type of market activity such as volume or open interest) and analyzes the options market from a data-driven perspective. The app populates three major analyses: 1) market maker (MM)'s expected gamma exposure, 2) market delta, 3) theoretical price vs. actual premium. The app has been built with Streamlit and deployed on the Heroku server.

# Background
Among the regular retail investors who are little familiar with the options market, it's a general conception that underlying asset price impact the price of its options, but not vice versa. However, options trades actually do impact the price movement of its underlying assets as well because of market maker(MM)'s participation in the options market. 

If you are a retail investor who regularly trades options, it's likely that the counterparty of most of your trades have been the MMs. MMs are not like typical investors like you and I who aim for making capital gains by buying low selling high. Instead, MMs playes a unique role as a passive market participant and aim to make money from a tiny fraction from the bid-ask spreads of our trades. Since the main source of their profit is not from making capital gains, they like to stay neutral by hedging their market exposure. Their hedging activities are called dynamic delta hedging (and gamma hedging). They pretty much seat in the backseat and let the market does whatever it wants to do. Then, just react by constantly hedging their positions. The way they hedge their positions is by buying and selling the underlying assets based on the deltas of their option positions. 

Let me give you a simple example. Let's assume I am buying an APPL call option and a MM is my counterparty who is selling the call option to me. Without any hedging, the MM will lose money if APPL stock moves up. Therefore, the MM would go out to the stock market and buy APPL shares to hedge his APPL short call position. With the hedging, regardless of the APPL stock moving up or down, the MM's exposure to AAPL stock price movement is almost neutral. It's a very simple example but what does that tell you? It means my call option buying on APPL stocks actually caused someone else to buy more AAPL shares.    

With the recent explosive growth in retail investor's US equity options (including ETF options) trading volumes, it is becoming increasingly important to understand how overall options market activity can impact the stock market.

## Gamma Squeeze in 2021 
During the meme stock gamma squeeze frenzy during Covid, there have been massive out-of-the-money call options on AMC and GME bought by retail investors. Since the MMs were one of the main counterparties of the massive call buying, they took massive short call positions on the same underluing stocks. To hedge the risk, they had to buy huge amount of the underlying stocks. As the market constantly moves and so as delta of those options, MMs have to passively protect themselves by making frequent trades as well. Many of those meme stocks skyrocketed (GME went up from a dollar to $66 at some point) fueled by retail investors' rage against the Hedge Funds (I am not going in too much in detail of their reasoning as there is a great Netflix show about this topic). Many of those retail investors spent their life savings on near term out-of-the-money calls (Side note: near term out-of-the-money calls are very cheap compared to longer-term in-the-money calls because it has the worst odds of winning). 

Well.. luck or skills, those stocks actually exploded. That pushed those out-of-money calls to be at-the-money or even in-the-money at much higher delta. At higher delta, MMs were forced to buy even more underlying stocks. That wasn't the end. As those options became more at-the-money, gamma also exploded (Gamma is sensitivity of changes in delta to a unit change in the underlying stock price and it's highest when the option is at-the-money) and MMs' stock buying became even crazier. 

 
## JPMorgan Hedged Equity Fund 
I also encourage you to learn JPMorgan Hedged Equity Fund's (JHEQX) Impact On S&P500 (https://tdameritradenetwork.com/video/jpmorgan-hedged-equity-fund-s-jheqx-impact-on-volatility-s-p-500) as it explains the impact of some of the mega funds' options trade activities to the market very well. In the example of the JPM fund, they take short call and long put positions which means market makers are on long call (positive gamma) and short put (negative gamma).

In my net gamma exposure analysis, I assume that MMs are on negative gamma for puts and positive gamma for calls (Note: This assumption may be only valid for index ETFs such as SPY and may not work for individual stocks). When an option is in net negative gamma territory, MMs' trend-following stance can cause some extra volatility to the market. Trend following is where more assets are bought when the asset price goes up, and sold more when the asset price goes down. I believe MMs' net gamma was far negative during December 2022 which generated even more equity selling in the midst of the overall market downturn. 


# App Development Process

## Quick view of required files
[![files-needed-for-deployment.jpg](https://i.postimg.cc/Xq50VwsD/files-needed-for-deployment.jpg)](https://postimg.cc/vxGKh6FW)

## How to run a streamlit app on your local machine
- Use the following command in command line
```
run streamlit [py file name].py
```

## Credit for tda-api package
- Credit to alexgolec/tda-api for the TD API package
- https://github.com/alexgolec/tda-api
- https://tda-api.readthedocs.io/en/v1.3.0/index.html![image](https://user-images.githubusercontent.com/82781419/208785245-00291777-f347-4981-8e5d-08fb38eaf44d.png)

## TD Authentication Process
- You need a Chrome driver (same version as your Chrome browser) in the same file location.
- If first time authenticating, you need to provide a dummy token json file name as part of the token_path. 
- When you run through the authentication process for the first time, it will pop out a chrome window for logging into the TD (client side, not the developer side) and approve API authentication.

## Heroku Deployment Process
### Heroku Deployment Item #1 - Hide credentials in the environment variables (aka config variables)
- If you are not using heroku for deployment, you can use load_dotenv() to hide your credentials.
- Note: Heroku doesn't allow dotenv() for some reason. Thankfully, Heroku proide native config variables.
-- Config Variables in Heroku
        - Created config variables --> Heroku --> App --> Settings --> Config Variables
    [![where-to-store-heroku-config-variables.jpg](https://i.postimg.cc/mgHjrPwF/where-to-store-heroku-config-variables.jpg)](https://postimg.cc/dhJrHtgq)
    To access config variables in Python app file:
        - os.environ.get([key for the variable])
    Need a tda-api token refresher json file as one of the cofig variables
        - Key = token_path
        - value = ./td_token.json


### Heroku Deployment Item #2 - Deploying Selenium webdriver in Heroku
- Need to add the latest Chrome build packs as Config Vars
- CHROMEDRIVER_PATH = /app/.chromedriver/bin/chromedriver
- GOOGLE_CHROME_BIN = /app/.apt/usr/bin/google-chrome
- Need to build a custom webdriver for proper deployment
```
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
```

### Heroku Deployment Item #3 - Callback URL Set up for TD Developers 
- Navigate to TD Developers, then your app.
- I set the callback url to: 	https://option-app-v1.herokuapp.com/

### Heroku Deployment Item #4 - Set up Procfile  
- Added the following configuration string to the Procfile 
```web: sh setup.sh && streamlit run --server.port $PORT app.py```

### Heroku Deployment Item #5 - Set up setup.sh for Streamlit configuration   
- Add below to the setup.sh which will make the dark theme as default 
```mkdir -p ~/.streamlit/
echo "[server]"  > ~/.streamlit/config.toml
echo "headless = true"  >> ~/.streamlit/config.toml
echo "port = $PORT"  >> ~/.streamlit/config.toml
echo "enableCORS = false"  >> ~/.streamlit/config.toml
echo "[theme]
base = 'dark'" >> ~/.streamlit/config.toml
```
### Heroku Deployment Item #6 - Create requirements.txt   
- Use pip freeze to create a text file for a list of all Python packages.
- Use the following command in command line
```
pip freeze >requirements.txt
```

