import pandas as pd

# -------- LOAD REAL DATA --------
url = "https://stooq.com/q/d/l/?s=%5Ensei&i=d"
df = pd.read_csv(url)

# -------- CHECK COLUMNS --------
print("Columns in data:", df.columns)

# -------- FIX COLUMN NAMES SAFELY --------
df.rename(columns={
    "Date": "datetime",
    "date": "datetime",
    "DATE": "datetime",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume"
}, inplace=True)

# -------- ENSURE datetime EXISTS --------
if "datetime" not in df.columns:
    print("ERROR: datetime column not found")
    exit()

# -------- CLEAN DATA --------
df = df.dropna()
df = df.sort_values(by="datetime")

# -------- EMA --------
df["ema9"] = df["close"].ewm(span=9).mean()
df["ema21"] = df["close"].ewm(span=21).mean()

# -------- STRATEGY --------
trades = []
position = None
entry_price = 0

for i in range(1, len(df)):

    # BUY
    if df["ema9"].iloc[i] > df["ema21"].iloc[i] and df["ema9"].iloc[i-1] <= df["ema21"].iloc[i-1]:
        position = "BUY"
        entry_price = df["close"].iloc[i]

    # SELL
    elif df["ema9"].iloc[i] < df["ema21"].iloc[i] and df["ema9"].iloc[i-1] >= df["ema21"].iloc[i-1]:
        if position == "BUY":
            exit_price = df["close"].iloc[i]
            profit = exit_price - entry_price
            trades.append(profit)
            position = None

# -------- RESULTS --------
total_profit = sum(trades)
total_trades = len(trades)
wins = len([t for t in trades if t > 0])

win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

print("Total Trades:", total_trades)
print("Profit:", total_profit)
print("Win Rate:", round(win_rate, 2), "%")
print("Backtest completed")
