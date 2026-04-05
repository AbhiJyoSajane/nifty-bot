import os
import time
from kiteconnect import KiteConnect

# ====== CONFIG FROM RAILWAY ======
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
REQUEST_TOKEN = os.getenv("REQUEST_TOKEN")

print("API_KEY:", API_KEY)
print("REQUEST_TOKEN:", REQUEST_TOKEN)

# ====== LOGIN ======
kite = KiteConnect(api_key=API_KEY)

try:
    data = kite.generate_session(REQUEST_TOKEN, api_secret=API_SECRET)
    access_token = data["access_token"]
    kite.set_access_token(access_token)

    print("✅ Login Successful")
except Exception as e:
    print("❌ Token Error:", e)
    exit()

# ====== STRATEGY START ======
print("🚀 Strategy Started")

while True:
    try:
        print("Running strategy loop...")

        # ===== PLACE YOUR LOGIC HERE =====
        # Example dummy:
        # ltp = kite.ltp("NSE:NIFTY 50")
        # print(ltp)

        time.sleep(10)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
