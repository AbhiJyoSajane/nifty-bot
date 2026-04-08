from kiteconnect import KiteConnect
import pandas as pd
import datetime
import os

# =========================
# CONFIG
# =========================
api_key = os.environ.get("API_KEY")
api_secret = os.environ.get("API_SECRET")
request_token = os.environ.get("REQUEST_TOKEN")

kite = KiteConnect(api_key=api_key)

data = kite.generate_session(request_token, api_secret=api_secret)
kite.set_access_token(data["access_token"])

print("✅ Connected")

# =========================
# SETTINGS
# =========================
NIFTY = 256265
TARGET = 30
SL = 15
OPTION_MULTIPLIER = 0.5
LOT_SIZE = 65   # 🔥 updated

# =========================
# FETCH DATA
# =========================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=30)

data = kite.historical_data(
    instrument_token=NIFTY,
    from_date=from_date,
    to_date=to_date,
    interval="5minute"
)

df = pd.DataFrame(data)

if df.empty:
    print("❌ No data")
    exit()

df.columns = [col.lower() for col in df.columns]

# =========================
# INDICATORS
# =========================
df['ema9'] = df['close'].ewm(span=9).mean()
df['ema21'] = df['close'].ewm(span=21).mean()
df['ema200'] = df['close'].ewm(span=200).mean()
df['adx'] = abs(df['ema9'] - df['ema21'])

# =========================
# BACKTEST
# =========================
position = None
entry_price = 0
total_pnl_points = 0
trades = []

for i in range(1, len(df)):

    row = df.iloc[i]
    price = row['close']

    # ENTRY
    if position is None:

        if row['ema9'] > row['ema21'] and price > row['ema200'] and row['adx'] > 10:
            position = "CE"
            entry_price = price

        elif row['ema9'] < row['ema21'] and price < row['ema200'] and row['adx'] > 10:
            position = "PE"
            entry_price = price

    # EXIT
    elif position:

        move = price - entry_price

        # TARGET
        if move >= TARGET:
            pnl = TARGET * OPTION_MULTIPLIER
            total_pnl_points += pnl
            trades.append(pnl)
            position = None

        # STOP LOSS
        elif move <= -SL:
            pnl = -SL * OPTION_MULTIPLIER
            total_pnl_points += pnl
            trades.append(pnl)
            position = None

# =========================
# RESULT
# =========================
total_pnl_rupees = total_pnl_points * LOT_SIZE

print("\n📊 OPTION BACKTEST (₹ RESULT)\n")

print(f"Total Trades: {len(trades)}")
print(f"Total PnL (Points): {round(total_pnl_points,2)}")
print(f"Total PnL (₹): {round(total_pnl_rupees,2)}")

wins = len([x for x in trades if x > 0])
losses = len([x for x in trades if x < 0])

print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if len(trades) > 0:
    print(f"Win Rate: {round((wins/len(trades))*100,2)}%")
