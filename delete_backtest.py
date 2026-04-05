from kiteconnect import KiteConnect

API_KEY = "btj1h6qbwop4gah2"
API_SECRET = "3r0r7i5b13ll8um9r6wtwrtwv51rv4ev"
REQUEST_TOKEN = "Q1buW6InimC1SX1a3C2WVyD1qOpOYke0"

kite = KiteConnect(api_key=API_KEY)

data = kite.generate_session(REQUEST_TOKEN, api_secret=API_SECRET)
ACCESS_TOKEN = data["access_token"]

kite.set_access_token(ACCESS_TOKEN)

print("✅ Connected successfully")
print(data["access_token"])
