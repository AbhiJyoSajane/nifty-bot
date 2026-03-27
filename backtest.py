import pandas as pd

# Load data (we will add CSV later)
df = pd.read_csv("data.csv")

capital = 100000
position = None
entry_price = 0
trades = []

for i in range(20, len(df)):

    recent_high = df["high"][i-20:i].max()
    recent_low = df["low"][i-20:i].min()
    price = df["close"][i]

    # BUY condition
    if position is None and price > recent_high:
        position = "BUY"
        entry_price = price

    # SELL condition
    elif position is None and price < recent_low:
        position = "SELL"
        entry_price = price

    # EXIT condition
    elif position == "BUY":
        if price < entry_price - 50 or price > entry_price + 100:
            profit = price - entry_price
            capital += profit
            trades.append(profit)
            position = None

    elif position == "SELL":
        if price > entry_price + 50 or price < entry_price - 100:
            profit = entry_price - price
            capital += profit
            trades.append(profit)
            position = None

print("Final Capital:", capital)
print("Total Trades:", len(trades))
print("Total Profit:", sum(trades))
