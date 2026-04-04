import pandas as pd
import yfinance as yf

# ===============================
# LOAD DATA (5 MIN)
# ===============================
df = yf.download("^NSEI", interval="5m", period="60d")

df = df.reset_index()

# FIX: handle tuple columns (yfinance issue)
df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]

df = df.rename(columns={
    "datetime": "date",
    "adj close": "adj_close"
})

df = df.dropna()
df['date'] = pd.to_datetime(df['date'])

# ===============================
# FILTER MARKET HOURS
# ===============================
df = df[(df['date'].dt.time >= pd.to_datetime("09:15").time()) &
        (df['date'].dt.time <= pd.to_datetime("15:30").time())]

# ===============================
# EMA CALCULATION
# ===============================
df['ema9'] = df['close'].ewm(span=9).mean()
df['ema21'] = df['close'].ewm(span=21).mean()

# ===============================
# VARIABLES
# ===============================
position = None
entry_price = 0
trades = []

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

    day = row['date'].date()
    time = row['date'].time()

    # Reset daily values
    if current_day != day:
        current_day = day
        daily_loss = 0
        trade_count = 0
        first_15_high = None
        first_15_low = None
        position = None

    # Capture 1st 15 min (9:15–9:30)
    if time <= pd.to_datetime("09:30").time():
        if first_15_high is None:
            first_15_high = row['high']
            first_15_low = row['low']
        else:
            first_15_high = max(first_15_high, row['high'])
            first_15_low = min(first_15_low, row['low'])

    # Trading window
    if not ((pd.to_datetime("09:30").time() <= time <= pd.to_datetime("11:30").time()) or
            (pd.to_datetime("14:00").time() <= time <= pd.to_datetime("15:15").time())):
        continue

    # Risk control
    if daily_loss <= max_daily_loss or trade_count >= 5:
        continue

    # ===============================
    # ORB STRATEGY (9:30–10:00)
    # ===============================
    if pd.to_datetime("09:30").time() <= time <= pd.to_datetime("10:00").time():

        if position is None:

            # BUY breakout
            if row['close'] > first_15_high and row['ema9'] > row['ema21']:
                position = "BUY"
                entry_price = row['close']
                trade_count += 1

            # SELL breakout
            elif row['close'] < first_15_low and row['ema9'] < row['ema21']:
                position = "SELL"
                entry_price = row['close']
                trade_count += 1

    # ===============================
    # EMA CROSSOVER BACKUP
    # ===============================
    elif time > pd.to_datetime("10:00").time():

        if position is None:

            # BUY crossover
            if row['ema9'] > row['ema21'] and prev['ema9'] <= prev['ema21']:
                position = "BUY"
                entry_price = row['close']
                trade_count += 1

            # SELL crossover
            elif row['ema9'] < row['ema21'] and prev['ema9'] >= prev['ema21']:
                position = "SELL"
                entry_price = row['close']
                trade_count += 1

    # ===============================
    # EXIT (EMA reverse)
    # ===============================
    if position == "BUY" and row['ema9'] < row['ema21']:
        pnl = row['close'] - entry_price
        trades.append(pnl)
        daily_loss += pnl
        position = None

    elif position == "SELL" and row['ema9'] > row['ema21']:
        pnl = entry_price - row['close']
        trades.append(pnl)
        daily_loss += pnl
        position = None

# ===============================
# RESULTS
# ===============================
total_trades = len(trades)
total_profit = sum(trades)
wins = len([t for t in trades if t > 0])
losses = len([t for t in trades if t < 0])

win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

print("\n===== FINAL RESULT =====")
print("Total Trades:", total_trades)
print("Winning Trades:", wins)
print("Losing Trades:", losses)
print("Win Rate:", round(win_rate, 2), "%")
print("Total Profit:", total_profit)
