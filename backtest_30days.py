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
LOT_SIZE = 65

START_CAPITAL = 20000
capital = START_CAPITAL

# Assume avg premium
AVG_PREMIUM = 120
TRADE_CAPITAL = AVG_PREMIUM * LOT_SIZE  # ~₹7800

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

total_pnl = 0
trades = []
skipped_trades = 0

for i in range(1, len(df)):

    row = df.iloc[i]
    price = row['close']

    # ENTRY
    if position is None:

        # Check capital availability
        if capital < TRADE_CAPITAL:
            skipped_trades += 1
            continue

        if row['ema9'] > row['ema21'] and price > row['ema200'] and row['adx'] > 10:
            position = "CE"
            entry_price = price
            capital -= TRADE_CAPITAL  # block capital

        elif row['ema9'] < row['ema21'] and price < row['ema200'] and row['adx'] > 10:
            position = "PE"
            entry_price = price
            capital -= TRADE_CAPITAL  # block capital

    # EXIT
    elif position:

        move = price - entry_price

        # TARGET
        if move >= TARGET:
            pnl = TARGET * OPTION_MULTIPLIER * LOT_SIZE
            capital += TRADE_CAPITAL + pnl
            total_pnl += pnl
            trades.append(pnl)
            position = None

        # STOP LOSS
        elif move <= -SL:
            pnl = -SL * OPTION_MULTIPLIER * LOT_SIZE
            capital += TRADE_CAPITAL + pnl
            total_pnl += pnl
            trades.append(pnl)
            position = None

# =========================
# RESULT
# =========================
print("\n📊 CAPITAL BASED BACKTEST\n")

print(f"Starting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total Profit/Loss: ₹{round(total_pnl,2)}")

print(f"\nTotal Trades Taken: {len(trades)}")
print(f"Skipped Trades (no capital): {skipped_trades}")

wins = len([x for x in trades if x > 0])
losses = len([x for x in trades if x < 0])

print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if len(trades) > 0:
    win_rate = (wins / len(trades)) * 100
    print(f"Win Rate: {round(win_rate,2)}%")
