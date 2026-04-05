import os
import time
from kiteconnect import KiteConnect

# ==============================
# CONFIG (from Railway variables)
# ==============================
API_KEY = os.environ.get("API_KEY")
API_SECRET = os.environ.get("API_SECRET")
REQUEST_TOKEN = os.environ.get("REQUEST_TOKEN")

# ==============================
# LOGIN + ACCESS TOKEN GENERATION
# ==============================
kite = KiteConnect(api_key=API_KEY)

try:
    data = kite.generate_session(REQUEST_TOKEN, api_secret=API_SECRET)
    access_token = data["access_token"]
    kite.set_access_token(access_token)
    print("✅ Access Token Generated")
except Exception as e:
    print("❌ Token Error:", e)
    exit()

# ==============================
# STRATEGY SETTINGS
# ==============================
TARGET = 30     # points
SL = 15         # points

# ==============================
# HELPER FUNCTION
# ==============================
def get_ltp(symbol):
    try:
        return kite.ltp(symbol)[symbol]["last_price"]
    except:
        return None

# ==============================
# MAIN STRATEGY LOOP
# ==============================
print("🚀 Strategy Started")

position = None
entry_price = 0

while True:
    try:
        # Example: NIFTY ATM CE/PE (you can improve later)
        ce_symbol = "NFO:NIFTY24APRATMCE"
        pe_symbol = "NFO:NIFTY24APRATMPE"

        ce_price = get_ltp(ce_symbol)
        pe_price = get_ltp(pe_symbol)

        if not ce_price or not pe_price:
            print("⚠ No data, retry...")
            time.sleep(5)
            continue

        print(f"CE: {ce_price} | PE: {pe_price}")

        # ENTRY LOGIC (simple premium momentum)
        if position is None:
            if ce_price > pe_price:
                position = "CE"
                entry_price = ce_price
                print(f"🟢 BUY CE @ {entry_price}")

            elif pe_price > ce_price:
                position = "PE"
                entry_price = pe_price
                print(f"🔴 BUY PE @ {entry_price}")

        # EXIT LOGIC
        if position == "CE":
            ltp = ce_price
            if ltp >= entry_price + TARGET:
                print("✅ TARGET HIT CE")
                position = None

            elif ltp <= entry_price - SL:
                print("❌ SL HIT CE")
                position = None

        elif position == "PE":
            ltp = pe_price
            if ltp >= entry_price + TARGET:
                print("✅ TARGET HIT PE")
                position = None

            elif ltp <= entry_price - SL:
                print("❌ SL HIT PE")
                position = None

        time.sleep(5)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
