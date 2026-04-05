from kiteconnect import KiteConnect

API_KEY = "YOUR_API_KEY"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

print("Kite connected successfully")
