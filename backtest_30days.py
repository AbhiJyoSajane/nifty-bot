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

# Generate access token
data = kite.generate_session(request_token, api_secret=api_secret)
kite.set_access_token(data["access_token"])

print("✅ Connected")

# =========================
# SETTINGS
# =========================
NIFTY = 256265
TARGET = 30
SL = 15

# =========================
# FETCH DATA (30 DAYS)
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
    print("❌ No data fetched")
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
# BACKTEST LOGIC
# =========================
position = None
entry_price = 0
total_pnl = 0
wins = 0
losses = 0
trade_count = 0

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

        # TARGET
        if price >= entry_price + TARGET:
            total_pnl += TARGET
            wins += 1
            trade_count += 1
            position = None

        # STOP LOSS
        elif price <= entry_price - SL:
            total_pnl -= SL
            losses += 1
            trade_count += 1
            position = None

# =========================
# RESULT
# =========================
print("\n📊 FINAL RESULT\n")

print(f"Total Trades: {trade_count}")
print(f"Total PnL: {total_pnl}")
print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if trade_count > 0:
    win_rate = (wins / trade_count) * 100
    print(f"Win Rate: {round(win_rate,2)}%")
else:
    print("No trades found")
