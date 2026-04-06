import os
from kiteconnect import KiteConnect

api_key = os.environ.get("API_KEY")

kite = KiteConnect(api_key=api_key)

print("LOGIN URL:")
print(kite.login_url())
