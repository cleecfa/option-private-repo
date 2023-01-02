# Description
This is a real-time web application that pulls options quotes, greeks and underluing asset info all based on user parameters (i.e. ticker, expirations dates, type of market activities such as volume or open interest) and analyze the options market from a data-driven persepctive. The app populates three different major analysis - 1) market maker(MM)'s expected gamma exposure, 2) market delta, 3) theoretical price vs. actual premium. The app has been built with Steramlit and deployed on Heroku server. 

# Background
The recent explosive growth in retail investor's US equity options (including ETF options) trading volumes, it is becoming more and more important to understand how the overall options market activities could impact the stock market. Many people misunderstand that it's only the case that stock price movement (in a case of where stock is an underlying asset whereas the underlying could be any asset these days) impacts the price of its options because options are called "derivatives" of its underlying asset. Anyway, what ended up happening is those meme stock prices exploded which moved those out-of-money calls to higher deltas, probably most of them ended up becoming in-the-money.

## Gamma Squeeze in 2021 
During the meme stock gamma squeeze frenzy during Covid, there have been massive out-of-the-money call options on AMC and GME bought by retail investors. It created massive short call positions on the MM side. MMs are those who are usually on the other side of retail investors' trades and participates in the market as a major liquidity provider. MMs don't usually aim to make a profit in the form of capital gains. The way they make money is by taking a small cut of the spread of millions of trades. I not going in too much down in the weeds of what they do but one thing I would like to highlight is that they are a passive market participant who need to avoid as much market risk as possible. In the example of the meme stock gamma squeeze, since the MMs were one of the main counterparties of the massive call buying, they had to take massive short call positions on the same underluing stocks. To hedge against the price risk for holding those massive short call positions, they had to buy huge amount of the underlying stocks. This activity is called delta-neutral hedging. As the market constantly moves and so as delta of those options, MMs have to passively protect themselves by making frequent trades as well. Many of those meme stocks skyrocketed (GME went up from a dollar to $66 at some point) fueled by retail investors' rage against the Hedge Funds (I am not going in too much in detail of their reasoning as there is a great Netflix show about this topic). Many of those retail investors happened to go near all-in (I don't believe they knew what they were doing .. they just happened take a huge bet on such a crazy deal without fully understanding the amount of risks involved) on near term out-of-the-money calls because they are the cheapest. Side note - near term out-of-the-money calls are very cheap compared to longer-term in-the-money calls because it has the worst odds of winning. That's why keep saying they did not know what they were doing lol. No educated investor can ever put their life savings on such a risky deal, probably at less than 10 delta (10 delta means the probability of maturing in the money is at less than 10% chance). 

Regardless of luck or skills, those stocks exploded. That means those out-of-money calls became at-the-money or even in-the-money at much higher delta. At higher delta, MMs were forced to buy more underlying stocks. That wasn't the end. As those options became more at-the-money, gamma also exploded (Gamma is sensitivity of changes in delta to a unit change in the underlying stock price and it's highest when the option is at-the-money) and MMs' stock buying became even crazier. 

So yes, options could also impact the price of underlying assets. 
 
## JPM 
I also encourage you to learn JPMorgan Hedged Equity Fund's (JHEQX) Impact On S&P500 (https://tdameritradenetwork.com/video/jpmorgan-hedged-equity-fund-s-jheqx-impact-on-volatility-s-p-500) as it explains the impact of some of the mega funds' options trade activities to the market very well. In the example of the JPM fund, they take short call and long put positions which means market makers are on long call (positive gamma) and short put (negative gamma).
In my net gamma exposure analysis, I assume that MMs are on negative gamma for puts and positive gamma for calls (Note: This assumption may be only valid for index ETFs such as SPY and may not work for individual stocks). When an option is in net negative gamma territory, MMs' trend-following stance can cause some extra volatility to the market. Trend following is where more assets are bought when the asset price goes up, and sold more when the asset price goes down. I believe MMs' net gamma was far negative during December 2022 which generated even more equity selling in the midst of the overall market downturn. 

# Credit for tda-api package
- Credit to alexgolec/tda-api for the TD API package
- https://github.com/alexgolec/tda-api
- https://tda-api.readthedocs.io/en/v1.3.0/index.html![image](https://user-images.githubusercontent.com/82781419/208785245-00291777-f347-4981-8e5d-08fb38eaf44d.png)

# App.py

# Heroku Deployment Process

TD Authentication Process
- You need a Chrome driver (same version as your Chrome browser) in the same file location.
- If first time authenticating, you need to provide a dummy token json file name as part of the token_path. 
- When you run the script for the first time, it will pop out a chrome window for logging into the TD (client side, not the developer side)![image](https://user-images.githubusercontent.com/82781419/208785275-4956445d-a765-40c1-8343-374f23229aeb.png)


Heroku Deployment Item #1 - Hide credentials in the environment variables (aka config variables)
- For non-heroku deployment --> use load_dotenv()
- For heroku --> load_dotenv() #Create environment variable --> for some reason heroku doesn't allow dotenv library
    Config Variables in Heroku
        - Created config variables --> Heroku --> App --> Settings --> Config Variables
    To access config variables in Python app file
        - os.environ.get([key for the variable])
    Where in the deployment process to generate a tda-api token refresher json file
        - ./td_token.json![image](https://user-images.githubusercontent.com/82781419/208785307-97e677f2-86fa-408f-bedb-13c4f696f09f.png)


Heroku Deployment Item #2 - Deploying Selenium webdriver in Heroku
- Need to add Chrome build packs as Config Vars
- CHROMEDRIVER_PATH = /app/.chromedriver/bin/chromedriver
- GOOGLE_CHROME_BIN = /app/.apt/usr/bin/google-chrome
- Need to build a custom webdriver for the deployment to work
- Reference: https://www.andressevilla.com/running-chromedriver-with-python-selenium-on-heroku/![image](https://user-images.githubusercontent.com/82781419/208785322-04c620c3-4f36-4cb9-b533-321aa8e11837.png)


Callback URL Set up for TD Developers 
- Set it to "https://<your heroku app name>.herokuapp.com/auth"![image](https://user-images.githubusercontent.com/82781419/208785350-990fe49b-45c6-4b5e-807e-e5bc3c5145ac.png)

