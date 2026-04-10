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

TARGET = 50
SL = 30

START_CAPITAL = 20000
capital = START_CAPITAL

MAX_TRADES_PER_DAY = 5
MAX_DAILY_LOSS = -2000

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

daily_pnl = 0
daily_trades = 0
current_day = None

for i in range(1, len(df)):

    row = df.iloc[i]
    price = row['close']
    date = row['date'].date()

    # ===== RESET DAILY =====
    if current_day != date:
        current_day = date
        daily_pnl = 0
        daily_trades = 0
        position = None

    # ===== STOP CONDITIONS =====
    if daily_trades >= MAX_TRADES_PER_DAY:
        continue

    if daily_pnl <= MAX_DAILY_LOSS:
        continue

    # ===== ENTRY =====
    if position is None:

        # BUY
        if row['ema9'] > row['ema21'] and price > row['ema200'] and row['adx'] > 10:
            position = "CE"
            entry_price = price

        # SELL
        elif row['ema9'] < row['ema21'] and price < row['ema200'] and row['adx'] > 10:
            position = "PE"
            entry_price = price

    # ===== EXIT =====
    elif position:

        exit_trade = False

        # TARGET
        if price >= entry_price + TARGET:
            pnl = TARGET
            wins += 1
            exit_trade = True

        # STOP LOSS
        elif price <= entry_price - SL:
            pnl = -SL
            losses += 1
            exit_trade = True

        if exit_trade:
            total_pnl += pnl
            capital += pnl
            daily_pnl += pnl

            trade_count += 1
            daily_trades += 1

            position = None

# =========================
# RESULT
# =========================
print("\n📊 CONTROLLED EMA STRATEGY RESULT\n")

print(f"Starting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total PnL: ₹{round(total_pnl,2)}")

print(f"\nTotal Trades: {trade_count}")
print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if trade_count > 0:
    win_rate = (wins / trade_count) * 100
    print(f"Win Rate: {round(win_rate,2)}%")
else:
    print("No trades found")
