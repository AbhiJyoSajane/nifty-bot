import pandas as pd

# === LOAD DATA ===
df = pd.read_csv("data.csv")

# Fix Yahoo format
df.rename(columns={
    "Date": "datetime",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close"
}, inplace=True)

df = df.dropna()

# === EMA ===
df["ema9"] = df["close"].ewm(span=9).mean()
df["ema21"] = df["close"].ewm(span=21).mean()

# === VARIABLES ===
trades = []
position = None
entry_price = 0

trades_today = 0
total_loss = 0
current_day = None

orb_high = None
orb_low = None

# === LOOP ===
for i in range(len(df)):
    row = df.iloc[i]

    date = row["datetime"][:10]

    # Reset daily
    if current_day != date:
        current_day = date
        trades_today = 0
        total_loss = 0
        orb_high = None
        orb_low = None

    price = row["close"]

    # ORB (first candle approx for daily data)
    if orb_high is None:
        orb_high = row["high"]
        orb_low = row["low"]
        continue

    # Trade control
    if trades_today >= 5 or total_loss <= -2000:
        continue

    # Trend
    uptrend = row["ema9"] > row["ema21"]
    downtrend = row["ema9"] < row["ema21"]

    # ENTRY
    if position is None:
        if price > orb_high and uptrend:
            position = "BUY"
            entry_price = price
            trades_today += 1

        elif price < orb_low and downtrend:
            position = "SELL"
            entry_price = price
            trades_today += 1

    # EXIT
    if position == "BUY":
        if price < entry_price - 20:
            trades.append(price - entry_price)
            total_loss += price - entry_price
            position = None
        elif price > entry_price + 40:
            trades.append(price - entry_price)
            position = None

    elif position == "SELL":
        if price > entry_price + 20:
            trades.append(entry_price - price)
            total_loss += entry_price - price
            position = None
        elif price < entry_price - 40:
            trades.append(entry_price - price)
            position = None

# === RESULTS ===
total_profit = sum(trades)
total_trades = len(trades)
wins = len([t for t in trades if t > 0])

print("Total Trades:", total_trades)
print("Profit:", total_profit)
print("Win Rate:", (wins/total_trades)*100 if total_trades > 0 else 0)
