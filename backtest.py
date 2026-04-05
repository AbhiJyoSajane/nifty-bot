import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from kiteconnect import KiteConnect

# ================= CONFIG =================
API_KEY = "your_api_key"
ACCESS_TOKEN = "your_access_token"
INSTRUMENT_TOKEN = 256265  # NIFTY50
INTERVAL = "5minute"

START_DATE = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
END_DATE = datetime.now().strftime('%Y-%m-%d')

MAX_DAILY_LOSS = -2000
MAX_TRADES = 5

# =========================================

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# ===== FETCH DATA =====
data = kite.historical_data(
    INSTRUMENT_TOKEN,
    START_DATE,
    END_DATE,
    INTERVAL
)

df = pd.DataFrame(data)
df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)

# ===== EMA =====
df['EMA9'] = df['close'].ewm(span=9).mean()
df['EMA21'] = df['close'].ewm(span=21).mean()

# ===== PREVIOUS DAY LEVELS =====
df['date_only'] = df.index.date

daily = df.groupby('date_only').agg({
    'high': 'max',
    'low': 'min'
})

daily['prev_high'] = daily['high'].shift(1)
daily['prev_low'] = daily['low'].shift(1)

# ===== WEEKLY LEVELS =====
df['week'] = df.index.to_series().dt.isocalendar().week

weekly = df.groupby('week').agg({
    'high': 'max',
    'low': 'min'
})

weekly['week_high'] = weekly['high'].shift(1)
weekly['week_low'] = weekly['low'].shift(1)

# ===== MERGE LEVELS =====
df = df.merge(daily[['prev_high', 'prev_low']], left_on='date_only', right_index=True)
df = df.merge(weekly[['week_high', 'week_low']], left_on='week', right_index=True)

# ===== BACKTEST =====
position = None
entry_price = 0
sl = 0
target = 0

total_profit = 0
trades = 0
wins = 0
losses = 0

current_day = None
daily_loss = 0
daily_trades = 0

orb_high = None
orb_low = None

for i in range(1, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i-1]

    day = row['date_only']

    # Reset daily
    if day != current_day:
        current_day = day
        daily_loss = 0
        daily_trades = 0
        orb_high = None
        orb_low = None

    # Stop if limits hit
    if daily_loss <= MAX_DAILY_LOSS or daily_trades >= MAX_TRADES:
        continue

    time = row.name.time()

    # ===== ORB RANGE (9:15 - 9:30) =====
    if time >= datetime.strptime("09:15", "%H:%M").time() and time <= datetime.strptime("09:30", "%H:%M").time():
        orb_high = max(orb_high or row['high'], row['high'])
        orb_low = min(orb_low or row['low'], row['low'])
        continue

    # ===== ENTRY =====
    if position is None and orb_high is not None:

        # BUY (ORB + EMA + Levels)
        if (
            row['close'] > orb_high and
            row['EMA9'] > row['EMA21'] and
            row['close'] > row['prev_high'] and
            row['close'] > row['week_high']
        ):
            position = "BUY"
            entry_price = row['close']
            sl = orb_low
            target = entry_price + (entry_price - sl)
            trades += 1
            daily_trades += 1

        # SELL
        elif (
            row['close'] < orb_low and
            row['EMA9'] < row['EMA21'] and
            row['close'] < row['prev_low'] and
            row['close'] < row['week_low']
        ):
            position = "SELL"
            entry_price = row['close']
            sl = orb_high
            target = entry_price - (sl - entry_price)
            trades += 1
            daily_trades += 1

        # ===== BACKUP EMA CROSS =====
        elif prev['EMA9'] < prev['EMA21'] and row['EMA9'] > row['EMA21']:
            position = "BUY"
            entry_price = row['close']
            sl = row['low']
            target = entry_price + (entry_price - sl)
            trades += 1
            daily_trades += 1

        elif prev['EMA9'] > prev['EMA21'] and row['EMA9'] < row['EMA21']:
            position = "SELL"
            entry_price = row['close']
            sl = row['high']
            target = entry_price - (sl - entry_price)
            trades += 1
            daily_trades += 1

    # ===== EXIT =====
    if position == "BUY":
        if row['low'] <= sl:
            profit = sl - entry_price
            losses += 1
            position = None
            daily_loss += profit
        elif row['high'] >= target:
            profit = target - entry_price
            wins += 1
            position = None

        total_profit += profit

    elif position == "SELL":
        if row['high'] >= sl:
            profit = entry_price - sl
            losses += 1
            position = None
            daily_loss += profit
        elif row['low'] <= target:
            profit = entry_price - target
            wins += 1
            position = None

        total_profit += profit

# ===== RESULT =====
print("\n===== FINAL RESULT =====")
print("Total Trades:", trades)
print("Winning Trades:", wins)
print("Losing Trades:", losses)
print("Win Rate:", round((wins / trades) * 100, 2) if trades else 0, "%")
print("Total Profit:", round(total_profit, 2))
