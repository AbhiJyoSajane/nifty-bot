from kiteconnect import KiteConnect
import pandas as pd
import datetime
import time
import os
import pytz

# =========================
# CONFIG
# =========================
api_key = os.environ.get("API_KEY")
api_secret = os.environ.get("API_SECRET")
request_token = os.environ.get("REQUEST_TOKEN")

kite = KiteConnect(api_key=api_key)

data = kite.generate_session(request_token, api_secret=api_secret)
access_token = data["access_token"]

kite.set_access_token(access_token)

print("✅ LOGIN SUCCESS")
print("✅ Connected")

# =========================
# SETTINGS
# =========================
NIFTY = 256265

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
        # TIME (IST FIX)
        # =========================
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.datetime.now(ist)

        to_date = now
        from_date = now - datetime.timedelta(minutes=300)

        # =========================
        # FETCH DATA
        # =========================
        data = kite.historical_data(
            instrument_token=NIFTY,
            from_date=from_date,
            to_date=to_date,
            interval="5minute"
        )

        df = pd.DataFrame(data)

        if df.empty:
            print("⚠️ No data received from Kite")
            time.sleep(60)
            continue

        df.columns = [col.lower() for col in df.columns]

        if 'close' not in df.columns:
            print("⚠️ Close column missing")
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

        print(f"📊 Price: {price:.2f} | EMA9: {row['ema9']:.2f} | EMA21: {row['ema21']:.2f}")

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
                if not quote:
                    print("❌ LTP not received")
                    time.sleep(10)
                    continue

                entry_price = list(quote.values())[0]['last_price']
                position = "CE"

                print(f"""
🟢 TRADE ENTRY
Type: CE
Strike: {strike}
Entry Price: {entry_price}
Target: {entry_price + TARGET}
Stop Loss: {entry_price - SL}
Symbol: {symbol}
""")

            # BUY PE
            elif (
                row['ema9'] < row['ema21'] and
                price < row['ema200'] and
                row['adx'] > 10
            ):
                symbol = f"NFO:NIFTY{EXPIRY}{int(strike)}PE"

                quote = kite.ltp(symbol)
                if not quote:
                    print("❌ LTP not received")
                    time.sleep(10)
                    continue

                entry_price = list(quote.values())[0]['last_price']
                position = "PE"

                print(f"""
🔴 TRADE ENTRY
Type: PE
Strike: {strike}
Entry Price: {entry_price}
Target: {entry_price + TARGET}
Stop Loss: {entry_price - SL}
Symbol: {symbol}
""")

        # =========================
        # EXIT
        # =========================
        elif position:

            quote = kite.ltp(symbol)

            if not quote:
                print("❌ LTP not received")
                time.sleep(10)
                continue

            current_price = list(quote.values())[0]['last_price']

            print(f"📈 Current: {current_price} | Entry: {entry_price}")

            # TARGET
            if current_price >= entry_price + TARGET:
                profit = current_price - entry_price
                total_pnl += profit

                print(f"""
🎯 TARGET HIT
Exit Price: {current_price}
Entry Price: {entry_price}
Profit: {profit}
Total PnL: {round(total_pnl,2)}
""")

                position = None
                symbol = None

            # STOPLOSS
            elif current_price <= entry_price - SL:
                loss = current_price - entry_price
                total_pnl += loss

                print(f"""
❌ STOP LOSS HIT
Exit Price: {current_price}
Entry Price: {entry_price}
Loss: {loss}
Total PnL: {round(total_pnl,2)}
""")

                position = None
                symbol = None

        time.sleep(60)

    except Exception as e:
        print("❌ Error:", e)
        time.sleep(60)
