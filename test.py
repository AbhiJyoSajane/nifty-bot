import os
from kiteconnect import KiteConnect

# ===== LOGIN =====
api_key = os.environ.get("btj1h6qbwop4gah2")
api_secret = os.environ.get("3r0r7i5b13ll8um9r6wtwrtwv51rv4ev")
request_token = os.environ.get("lABed3OluETo6DOSs2ZJ4i5z77MnDzv5")
print("DEBUG TOKEN:", request_token)
kite = KiteConnect(api_key=api_key)

try:
    data = kite.generate_session(request_token, api_secret=api_secret)
    access_token = data["access_token"]
    kite.set_access_token(access_token)

    print("✅ Login successful")

except Exception as e:
    print("❌ Token Error:", e)
    exit()

# ===== RUN YOUR STRATEGY =====
import strategy
