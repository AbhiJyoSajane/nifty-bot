from kiteconnect import KiteConnect
import datetime
import time
import os

# ================= CONFIG =================
api_key = os.environ.get("API_KEY")
access_token = os.environ.get("ACCESS_TOKEN")

kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

print("✅ BOT STARTED")

NIFTY = 256265
LOT_SIZE = 50

MAX_TRADES = 3
trade_count = 0

orb_high = None
orb_low = None

position = None
entry_price = 0
sl = 0
target = 0
tradingsymbol = None

# ================= HELPERS =================
def get_atm(price):
    return round(price / 50) * 50

def get_option_symbol(price, direction):
    atm = get_atm(price)

    if direction == "BUY":
        strike = atm - 100
        opt_type = "CE"
    else:
        strike = atm + 100
        opt_type = "PE"

    expiry = "25APR"  # ⚠️ UPDATE WEEKLY

    symbol = f"NIFTY{expiry}{strike}{opt_type}"
    return symbol

# ================= MAIN LOOP =================
while True:

    now = datetime.datetime.now().time()

    try:
        ltp = kite.ltp(["NSE:NIFTY 50"])
        price = ltp["NSE:NIFTY 50"]["last_price"]
    except:
        print("⚠️ LTP error")
        time.sleep(2)
        continue

    # ===== BUILD ORB =====
    if datetime.time(9,15) <= now <= datetime.time(9,45):
        if orb_high is None:
            orb_high = price
            orb_low = price
        else:
            orb_high = max(orb_high, price)
            orb_low = min(orb_low, price)

    # ===== ENTRY =====
    if position is None and trade_count < MAX_TRADES:

        if datetime.time(9,46) <= now <= datetime.time(11,30):

            # BUY
            if price > orb_high:
                tradingsymbol = get_option_symbol(price, "BUY")

                print("📈 BUY SIGNAL:", tradingsymbol)

                # PLACE ORDER
                order_id = kite.place_order(
                    variety=kite.VARIETY_REGULAR,
                    exchange=kite.EXCHANGE_NFO,
                    tradingsymbol=tradingsymbol,
                    transaction_type=kite.TRANSACTION_TYPE_BUY,
                    quantity=LOT_SIZE,
                    order_type=kite.ORDER_TYPE_MARKET,
                    product=kite.PRODUCT_MIS
                )

                entry_price = kite.ltp([f"NFO:{tradingsymbol}"])[f"NFO:{tradingsymbol}"]["last_price"]

                sl = entry_price - 20
                target = entry_price + 30

                position = "BUY"
                trade_count += 1

            # SELL
            elif price < orb_low:
                tradingsymbol = get_option_symbol(price, "SELL")

                print("📉 SELL SIGNAL:", tradingsymbol)

                order_id = kite.place_order(
                    variety=kite.VARIETY_REGULAR,
                    exchange=kite.EXCHANGE_NFO,
                    tradingsymbol=tradingsymbol,
                    transaction_type=kite.TRANSACTION_TYPE_BUY,
                    quantity=LOT_SIZE,
                    order_type=kite.ORDER_TYPE_MARKET,
                    product=kite.PRODUCT_MIS
                )

                entry_price = kite.ltp([f"NFO:{tradingsymbol}"])[f"NFO:{tradingsymbol}"]["last_price"]

                sl = entry_price - 20
                target = entry_price + 30

                position = "SELL"
                trade_count += 1

    # ===== EXIT =====
    elif position:

        current = kite.ltp([f"NFO:{tradingsymbol}"])[f"NFO:{tradingsymbol}"]["last_price"]

        # TRAILING
        if current > entry_price + 15:
            sl = entry_price

        if current >= target or current <= sl:

            print("🚪 EXIT:", tradingsymbol)

            kite.place_order(
                variety=kite.VARIETY_REGULAR,
                exchange=kite.EXCHANGE_NFO,
                tradingsymbol=tradingsymbol,
                transaction_type=kite.TRANSACTION_TYPE_SELL,
                quantity=LOT_SIZE,
                order_type=kite.ORDER_TYPE_MARKET,
                product=kite.PRODUCT_MIS
            )

            position = None

    time.sleep(2)
