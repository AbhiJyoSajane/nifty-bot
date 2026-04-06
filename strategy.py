from kiteconnect import KiteConnect
import pandas as pd
import datetime
import time

# =========================
# CONFIG
# =========================
import os

api_key = os.environ.get("API_KEY")
api_secret = os.environ.get("API_SECRET")
request_token = os.environ.get("REQUEST_TOKEN")

kite = KiteConnect(api_key=api_key)

data = kite.generate_session(request_token, api_secret=api_secret)
access_token = data["access_token"]

kite.set_access_token(access_token)

print("✅ LOGIN SUCCESS")

print("✅ Connected")

NIFTY = 256265  # NIFTY 50 instrument token

position = None
symbol = None
entry_price = 0
total_pnl = 0

TARGET = 30
SL = 15

# =========================
# GET WEEKLY EXPIRY
# =========================
def get_expiry():
    today = datetime.date.today()
    thursday = today + datetime.timedelta((3 - today.weekday()) % 7)
    return thursday.strftime("%d%b").upper()

EXPIRY = get_expiry()

# =========================
# MAIN LOOP
# =========================
while True:

    try:
        # =========================
        # FETCH DATA (5 MIN)
        # =========================
        data = kite.historical_data(
            instrument_token=NIFTY,
            from_date=datetime.datetime.now() - datetime.timedelta(minutes=120),
            to_date=datetime.datetime.now(),
            interval="5minute"
        )

        df = pd.DataFrame(data)

        if df.empty:
            print("⚠️ No data")
            time.sleep(60)
            continue

        df.columns = [col.lower() for col in df.columns]

        if 'close' not in df.columns:
            print("⚠️ Missing close")
            time.sleep(60)
            continue

        # =========================
        # INDICATORS
        # =========================
        df['ema9'] = df['close'].ewm(span=9).mean()
        df['ema21'] = df['close'].ewm(span=21).mean()
        df['ema200'] = df['close'].ewm(span=200).mean()
        df['adx'] = abs(df['ema9'] - df['ema21'])

        row = df.iloc[-1]
        price = row['close']

        # =========================
        # ENTRY
        # =========================
        if position is None:

            strike = round(price / 50) * 50

            # BUY CE
            if (
                row['ema9'] > row['ema21'] and
                price > row['ema200'] and
                row['adx'] > 10
            ):
                symbol = f"NFO:NIFTY{EXPIRY}{int(strike)}CE"

                quote = kite.ltp(symbol)
                entry_price = list(quote.values())[0]['last_price']

                position = "CE"
                print(f"🟢 BUY CE {strike} @ {entry_price}")

            # BUY PE
            elif (
                row['ema9'] < row['ema21'] and
                price < row['ema200'] and
                row['adx'] > 10
            ):
                symbol = f"NFO:NIFTY{EXPIRY}{int(strike)}PE"

                quote = kite.ltp(symbol)
                entry_price = list(quote.values())[0]['last_price']

                position = "PE"
                print(f"🔴 BUY PE {strike} @ {entry_price}")

        # =========================
        # EXIT
        # =========================
        elif position:

            quote = kite.ltp(symbol)
            current_price = list(quote.values())[0]['last_price']

            # TARGET
            if current_price >= entry_price + TARGET:
                profit = current_price - entry_price
                total_pnl += profit

                print(f"🎯 TARGET HIT @ {current_price} | PnL: {profit}")
                print(f"💰 TOTAL: {round(total_pnl,2)}")

                position = None
                symbol = None

            # STOPLOSS
            elif current_price <= entry_price - SL:
                loss = current_price - entry_price
                total_pnl += loss

                print(f"❌ SL HIT @ {current_price} | PnL: {loss}")
                print(f"💰 TOTAL: {round(total_pnl,2)}")

                position = None
                symbol = None

        time.sleep(60)

    except Exception as e:
        print("❌ Error:", e)
        time.sleep(60)
