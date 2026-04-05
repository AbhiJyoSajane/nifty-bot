import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta

# ===============================
# FETCH FREE DATA (NSE VIA STITCHED SOURCE)
# ===============================
def get_data():
    url = "https://stooq.com/q/d/l/?s=nifty&i=5"

    response = requests.get(url)
    df = pd.read_csv(StringIO(response.text))

    df.columns = [c.lower() for c in df.columns]
    df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
    df.set_index('datetime', inplace=True)

    # last 3 months
    df = df[df.index > (datetime.now() - timedelta(days=90))]

    return df

df = get_data()

# ===============================
# EMA
# ===============================
df['ema9'] = df['close'].ewm(span=9).mean()
df['ema21'] = df['close'].ewm(span=21).mean()

# ===============================
# DAILY + WEEKLY LEVELS
# ===============================
df['date'] = df.index.date

daily = df.groupby('date').agg({'high': 'max', 'low': 'min'}).shift(1)
df = df.merge(daily, left_on='date', right_index=True, suffixes=('', '_yday'))

df['week'] = pd.to_datetime(df.index).isocalendar().week
weekly = df.groupby('week').agg({'high': 'max', 'low': 'min'}).shift(1)
df = df.merge(weekly, left_on='week', right_index=True, suffixes=('', '_week'))

# ===============================
# BACKTEST
# ===============================
position = None
entry = 0
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

    day = row['date']

    # Reset daily
    if day != current_day:
        current_day = day
        daily_loss = 0
        daily_trades = 0
        orb_high = None
        orb_low = None

    if daily_loss <= -2000 or daily_trades >= 5:
        continue

    time = row.name.time()

    # ORB (first 15 min)
    if time <= datetime.strptime("09:30", "%H:%M").time():
        orb_high = max(orb_high or row['high'], row['high'])
        orb_low = min(orb_low or row['low'], row['low'])
        continue

    # ENTRY
    if position is None and orb_high is not None:

        # BUY
        if (
            row['close'] > orb_high and
            row['ema9'] > row['ema21'] and
            row['close'] > row['high_yday'] and
            row['close'] > row['high_week']
        ):
            position = "BUY"
            entry = row['close']
            sl = orb_low
            target = entry + (entry - sl)
            trades += 1
            daily_trades += 1

        # SELL
        elif (
            row['close'] < orb_low and
            row['ema9'] < row['ema21'] and
            row['close'] < row['low_yday'] and
            row['close'] < row['low_week']
        ):
            position = "SELL"
            entry = row['close']
            sl = orb_high
            target = entry - (sl - entry)
            trades += 1
            daily_trades += 1

        # BACKUP EMA CROSS
        elif prev['ema9'] < prev['ema21'] and row['ema9'] > row['ema21']:
            position = "BUY"
            entry = row['close']
            sl = row['low']
            target = entry + (entry - sl)
            trades += 1
            daily_trades += 1

        elif prev['ema9'] > prev['ema21'] and row['ema9'] < row['ema21']:
            position = "SELL"
            entry = row['close']
            sl = row['high']
            target = entry - (sl - entry)
            trades += 1
            daily_trades += 1

    # EXIT
    if position == "BUY":
        if row['low'] <= sl:
            pnl = sl - entry
            losses += 1
            daily_loss += pnl
            position = None
        elif row['high'] >= target:
            pnl = target - entry
            wins += 1
            position = None
        total_profit += pnl

    elif position == "SELL":
        if row['high'] >= sl:
            pnl = entry - sl
            losses += 1
            daily_loss += pnl
            position = None
        elif row['low'] <= target:
            pnl = entry - target
            wins += 1
            position = None
        total_profit += pnl

# ===============================
# RESULT
# ===============================
win_rate = (wins / trades * 100) if trades else 0

print("\n===== FINAL RESULT =====")
print("Total Trades:", trades)
print("Winning Trades:", wins)
print("Losing Trades:", losses)
print("Win Rate:", round(win_rate, 2), "%")
print("Total Profit:", round(total_profit, 2))
