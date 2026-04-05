from kiteconnect import KiteConnect

API_KEY = "btj1h6qbwop4gah2"
ACCESS_TOKEN = "pQ7LcW4G7PHA70VwvSvWQQW8mzQL7Ttz"

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# Test connection
profile = kite.profile()

print("✅ Connected to Zerodha")
print("User:", profile["user_name"])
