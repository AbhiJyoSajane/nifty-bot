from kiteconnect import KiteConnect
import pandas as pd
import datetime
import time

# =========================
# CONFIG
# =========================
API_KEY = "btj1h6qbwop4gah2"
ACCESS_TOKEN = "6Usfkw0Q3rKm18F1uIX5Q6VTtKZvdHEO"

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

print("✅ Paper Trading Started")

NIFTY = 256265  # NIFTY 50 instrument token

position = None
symbol = None
entry_premium = 0
total_pnl = 0

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
        # FETCH DATA
        # =========================
        data = kite.historical_data(
            instrument_token=NIFTY,
            from_date=datetime.datetime.now() - datetime.timedelta(minutes=120),
            to_date=datetime.datetime.now(),
            interval="5minute"
        )

        df = pd.DataFrame(data)

        # ===== FIX START =====
        if df.empty:
            print("⚠️ No data received, retrying...")
            time.sleep(60)
            continue

        df.columns = [col.lower() for col in df.columns]

        if 'close' not in df.columns:
            print("⚠️ Close column missing, retrying...")
            time.sleep(60)
            continue
        # ===== FIX END =====

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
            if row['ema9'] > row['ema21'] and price > row['ema200'] and row['adx'] > 10:
                symbol = f"NFO:NIFTY{EXPIRY}{int(strike)}CE"

                quote = kite.ltp(symbol)
                entry_premium = list(quote.values())[0]['last_price']

                position = "CE"
                print(f"🟢 BUY CE {strike} @ {entry_premium}")

            # BUY PE
            elif row['ema9'] < row['ema21'] and price < row['ema200'] and row['adx'] > 10:
                symbol = f"NFO:NIFTY{EXPIRY}{int(strike)}PE"

                quote = kite.ltp(symbol)
                entry_premium = list(quote.values())[0]['last_price']

                position = "PE"
                print(f"🔴 BUY PE {strike} @ {entry_premium}")

        # =========================
        # EXIT
        # =========================
        elif position:

            quote = kite.ltp(symbol)
            current_premium = list(quote.values())[0]['last_price']

            # TARGET +30 points
            if current_premium >= entry_premium + 30:
                profit = current_premium - entry_premium
                total_pnl += profit

                print(f"🎯 TARGET HIT | Exit @ {current_premium} | PnL: {profit}")
                print(f"💰 TOTAL PnL: {round(total_pnl,2)}")

                position = None
                symbol = None

            # SL -15 points
            elif current_premium <= entry_premium - 15:
                loss = current_premium - entry_premium
                total_pnl += loss

                print(f"❌ SL HIT | Exit @ {current_premium} | PnL: {loss}")
                print(f"💰 TOTAL PnL: {round(total_pnl,2)}")

                position = None
                symbol = None

        # =========================
        # LOOP WAIT
        # =========================
        time.sleep(60)

    except Exception as e:
        print("❌ Error:", e)
        time.sleep(60)
