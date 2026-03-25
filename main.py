import os
import time
from kiteconnect import KiteConnect

api_key = os.getenv("API_KEY")
access_token = os.getenv("ACCESS_TOKEN")

kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

while True:
    try:
        price = kite.ltp("NSE:INFY")["NSE:INFY"]["last_price"]
        print("INFY price:", price)

    except Exception as e:
        print("Error:", e)

    time.sleep(60)
