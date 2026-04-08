from kiteconnect import KiteConnect
import pandas as pd
import datetime
import os

# ================= CONFIG =================
api_key = os.environ.get("API_KEY")
api_secret = os.environ.get("API_SECRET")
request_token = os.environ.get("REQUEST_TOKEN")

kite = KiteConnect(api_key=api_key)
data = kite.generate_session(request_token, api_secret=api_secret)
kite.set_access_token(data["access_token"])

print("✅ Connected")

# ================= SETTINGS =================
NIFTY = 256265
LOT_SIZE = 65
START_CAPITAL = 20000
capital = START_CAPITAL

PREMIUM_FACTOR = 0.5

# ================= FETCH DATA =================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=30)

data = kite.historical_data(
    instrument_token=NIFTY,
    from_date=from_date,
    to_date=to_date,
    interval="5minute"
)

df = pd.DataFrame(data)
df.columns = [col.lower() for col in df.columns]

# ================= BACKTEST =================
position = None
entry_price = 0
sl_price = 0

orb_high = None
orb_low = None

trades = []

for i in range(30, len(df)):

    row = df.iloc[i]
    prev = df.iloc[i-1]

    price = row['close']
    time = row['date'].time()

    # ================= RESET DAILY =================
    if time == datetime.time(9,15):
        orb_high = row['high']
        orb_low = row['low']

    # ================= BUILD ORB =================
    if datetime.time(9,15) <= time <= datetime.time(9,30):
        orb_high = max(orb_high, row['high'])
        orb_low = min(orb_low, row['low'])

    # ================= VOLUME =================
    avg_vol = df['volume'].rolling(20).mean().iloc[i]
    high_vol = row['volume'] > avg_vol * 1.5

    # ================= ENTRY =================
    if position is None and datetime.time(9,35) <= time <= datetime.time(10,30):

        # BUY
        if price > orb_high and price > prev['high'] and high_vol:
            position = "BUY"
            entry_price = price
            sl_price = prev['low']

        # SELL
        elif price < orb_low and price < prev['low'] and high_vol:
            position = "SELL"
            entry_price = price
            sl_price = prev['high']

    # ================= EXIT =================
    elif position:

        premium_move = (price - entry_price) * PREMIUM_FACTOR

        # 🔴 BUY EXIT
        if position == "BUY":

            # SL HIT
            if price <= sl_price:
                pnl = premium_move * LOT_SIZE
                capital += pnl
                trades.append(pnl)
                position = None

            else:
                # 🔥 TRAILING SL (previous candle low)
                sl_price = max(sl_price, prev['low'])

        # 🔴 SELL EXIT
        elif position == "SELL":

            if price >= sl_price:
                pnl = premium_move * LOT_SIZE
                capital += pnl
                trades.append(pnl)
                position = None

            else:
                # 🔥 TRAILING SL (previous candle high)
                sl_price = min(sl_price, prev['high'])

# ================= RESULT =================
wins = len([x for x in trades if x > 0])
losses = len([x for x in trades if x < 0])

print("\n📊 PURE ORB BACKTEST (TRAILING)\n")

print(f"Starting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total PnL: ₹{round(capital - START_CAPITAL,2)}")

print(f"\nTotal Trades: {len(trades)}")
print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if len(trades) > 0:
    print(f"Win Rate: {round((wins/len(trades))*100,2)}%")
