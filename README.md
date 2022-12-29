*Credit for tda-api package*
- Credit to alexgolec/tda-api for the TD API package
- https://github.com/alexgolec/tda-api
- https://tda-api.readthedocs.io/en/v1.3.0/index.html![image](https://user-images.githubusercontent.com/82781419/208785245-00291777-f347-4981-8e5d-08fb38eaf44d.png)


*Heroku Deployment Process*

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

