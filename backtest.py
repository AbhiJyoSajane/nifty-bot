import pandas as pd
import yfinance as yf

# ===============================
# DATA
# ===============================
df = yf.download("^NSEI", interval="5m", period="60d")

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df.columns = [c.lower() for c in df.columns]
df.dropna(inplace=True)

df['date'] = df.index
df['date'] = pd.to_datetime(df['date'])

# ===============================
# EMA
# ===============================
df['ema9'] = df['close'].ewm(span=9).mean()
df['ema21'] = df['close'].ewm(span=21).mean()

# ===============================
# PREPARE DAILY / WEEKLY LEVELS
# ===============================
df['date_only'] = df['date'].dt.date

daily = df.groupby('date_only').agg({
    'high': 'max',
    'low': 'min'
}).shift(1)

df = df.merge(daily, on='date_only', suffixes=('', '_yday'))

df['week'] = df['date'].dt.isocalendar().week
weekly = df.groupby('week').agg({
    'high': 'max',
    'low': 'min'
}).shift(1)

df = df.merge(weekly, on='week', suffixes=('', '_week'))

# ===============================
# VARIABLES
# ===============================
position = None
entry_price = 0

total_profit = 0
total_trades = 0
wins = 0
losses = 0

daily_loss = 0
max_daily_loss = -2000
trade_count = 0

current_day = None
first_15_high = None
first_15_low = None

# ===============================
# LOOP
# ===============================
for i in range(1, len(df)):

    row = df.iloc[i]
    prev = df.iloc[i-1]

    time = row['date'].time()
    day = row['date'].date()

    # Reset daily
    if current_day != day:
        current_day = day
        daily_loss = 0
        trade_count = 0
        first_15_high = None
        first_15_low = None
        position = None

    # Capture ORB
    if time <= pd.to_datetime("09:30").time():
        if first_15_high is None:
            first_15_high = row['high']
            first_15_low = row['low']
        else:
            first_15_high = max(first_15_high, row['high'])
            first_15_low = min(first_15_low, row['low'])
        continue

    # Time filter
    if not ((pd.to_datetime("09:30").time() <= time <= pd.to_datetime("11:30").time()) or
            (pd.to_datetime("14:00").time() <= time <= pd.to_datetime("15:15").time())):
        continue

    # Risk control
    if daily_loss <= max_daily_loss or trade_count >= 5:
        continue

    # ===============================
    # ENTRY
    # ===============================
    if position is None:

        # BUY (ALL CONDITIONS)
        if (row['close'] > first_15_high and
            row['close'] > row['high_yday'] and
            row['close'] > row['high_week'] and
            row['ema9'] > row['ema21']):

            position = "BUY"
            entry_price = row['close']
            trade_count += 1
            total_trades += 1

        # SELL
        elif (row['close'] < first_15_low and
              row['close'] < row['low_yday'] and
              row['close'] < row['low_week'] and
              row['ema9'] < row['ema21']):

            position = "SELL"
            entry_price = row['close']
            trade_count += 1
            total_trades += 1

    # ===============================
    # BACKUP EMA STRATEGY
    # ===============================
    elif time > pd.to_datetime("10:00").time() and position is None:

        if row['ema9'] > row['ema21'] and prev['ema9'] <= prev['ema21']:
            position = "BUY"
            entry_price = row['close']
            trade_count += 1
            total_trades += 1

        elif row['ema9'] < row['ema21'] and prev['ema9'] >= prev['ema21']:
            position = "SELL"
            entry_price = row['close']
            trade_count += 1
            total_trades += 1

    # ===============================
    # EXIT
    # ===============================
    elif position == "BUY":
        if row['ema9'] < row['ema21']:
            pnl = row['close'] - entry_price
            total_profit += pnl
            if pnl > 0:
                wins += 1
            else:
                losses += 1
                daily_loss += pnl
            position = None

    elif position == "SELL":
        if row['ema9'] > row['ema21']:
            pnl = entry_price - row['close']
            total_profit += pnl
            if pnl > 0:
                wins += 1
            else:
                losses += 1
                daily_loss += pnl
            position = None

# ===============================
# RESULT
# ===============================
win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

print("\n===== FINAL RESULT =====")
print("Total Trades:", total_trades)
print("Winning Trades:", wins)
print("Losing Trades:", losses)
print("Win Rate:", round(win_rate, 2), "%")
print("Total Profit:", round(total_profit, 2))
