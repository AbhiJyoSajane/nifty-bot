import pandas as pd

# Load data
df = pd.read_csv("data.csv")

# Clean columns
df.columns = ["datetime","open","high","low","close","adj_close","volume"]
df = df.dropna()

price_history = []

trades = []
position = None
entry_price = 0

def avg_range(data, n=5):
    if len(data) < n:
        return 0
    return sum(d["high"] - d["low"] for d in data[-n:]) / n

def get_range(data, n=10):
    highs = [d["high"] for d in data[-n:]]
    lows = [d["low"] for d in data[-n:]]
    return max(highs), min(lows)

def is_sideways(data):
    if len(data) < 10:
        return False
    r_high, r_low = get_range(data)
    return (r_high - r_low) < avg_range(data, 5) * 3

for i, row in df.iterrows():
    candle = {
        "price": row["close"],
        "high": row["high"],
        "low": row["low"]
    }

    price_history.append(candle)

    if len(price_history) < 10:
        continue

    price = candle["price"]

    # Exit condition
    if position == "BUY" and price < entry_price:
        trades.append(price - entry_price)
        position = None

    elif position == "SELL" and price > entry_price:
        trades.append(entry_price - price)
        position = None

    if position:
        continue

    # Sideways
    if is_sideways(price_history):
        r_high, r_low = get_range(price_history)

        if price <= r_low:
            position = "BUY"
            entry_price = price

        elif price >= r_high:
            position = "SELL"
            entry_price = price

    else:
        avg = avg_range(price_history)

        if (candle["high"] - candle["low"]) > avg:
            if price > candle["high"] - 0.2:
                position = "BUY"
                entry_price = price

            elif price < candle["low"] + 0.2:
                position = "SELL"
                entry_price = price

# Results
total_profit = sum(trades)
total_trades = len(trades)
wins = len([t for t in trades if t > 0])
losses = len([t for t in trades if t <= 0])

print("Total Trades:", total_trades)
print("Profit:", total_profit)
print("Win Rate:", (wins/total_trades)*100 if total_trades else 0)
