import pandas as pd

# -------- LOAD REAL DATA (FREE SOURCE) --------
url = "https://stooq.com/q/d/l/?s=%5Ensei&i=5"

df = pd.read_csv(url)

# Fix column names
df.columns = ["datetime","open","high","low","close","volume"]

df = df.dropna()
df = df.sort_values("datetime")

# -------- STRATEGY --------
df["ema9"] = df["close"].ewm(span=9).mean()
df["ema21"] = df["close"].ewm(span=21).mean()

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

# -------- RESULT --------
total_profit = sum(trades)
total_trades = len(trades)
wins = len([t for t in trades if t > 0])

win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

print("Total Trades:", total_trades)
print("Profit:", total_profit)
print("Win Rate:", win_rate)
print("Backtest completed")
