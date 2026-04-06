import os
from kiteconnect import KiteConnect

# Read from Railway variables
api_key = os.environ.get("API_KEY")
api_secret = os.environ.get("API_SECRET")
request_token = os.environ.get("REQUEST_TOKEN")

print("DEBUG TOKEN:", request_token)

# Check if token exists
if not request_token:
    raise Exception("❌ REQUEST_TOKEN is missing in Railway variables")

# Create Kite session
kite = KiteConnect(api_key=api_key)

data = kite.generate_session(request_token, api_secret=api_secret)

print("✅ ACCESS TOKEN:")
print(data["access_token"])
