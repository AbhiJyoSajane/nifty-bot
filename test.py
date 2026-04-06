import os
from kiteconnect import KiteConnect

api_key = os.environ.get("API_KEY")
api_secret = os.environ.get("API_SECRET")
request_token = os.environ.get("REQUEST_TOKEN")

print("Starting token generation...")

kite = KiteConnect(api_key=api_key)

try:
    data = kite.generate_session(request_token, api_secret=api_secret)
    
    access_token = data["access_token"]
    
    print("ACCESS TOKEN:", access_token)

except Exception as e:
    print("ERROR:", e)
