import pandas as pd

# ==============================
# LOAD DATA
# ==============================
df = pd.read_csv("data.csv")

# Clean column names
df.columns = [col.lower().replace(" ", "").replace("*", "") for col in df.columns]

# Rename date column
if "date" in df.columns:
    df.rename(columns={"date": "datetime"}, inplace=True)

# Drop missing values
df = df.dropna()

print("Columns:", df.columns)
print("Total rows:", len(df))

# ==============================
# EMA CALCULATION
# ==============================
df["ema9"] = df["close"].ewm(span=9).mean()
df["ema21"] = df["close"].ewm(span=21).mean()

# ==============================
# VARIABLES
# ==============================
position = None
entry_price = 0
trades = []
max_trades = 5
daily_loss_limit = -2000
current_day_loss = 0
trade_count = 0

# ==============================
# LOOP (BACKTEST)
# ==============================
for i in range(20, len(df)):

    if trade_count >= max_trades:
        break

    row = df.iloc[i]
    price = row["close"]

    # ===== ENTRY =====
    if position is None:

        # BUY condition
        if row["ema9"] > row["ema21"]:
            position = "BUY"
            entry_price = price
            print("BUY at", price)

        # SELL condition
        elif row["ema9"] < row["ema21"]:
            position = "SELL"
            entry_price = price
            print("SELL at", price)

    # ===== EXIT =====
    elif position == "BUY":
        profit = price - entry_price

        if profit <= -20 or row["ema9"] < row["ema21"]:
            trades.append(profit)
            current_day_loss += profit
            trade_count += 1
            print("EXIT BUY:", profit)
            position = None

    elif position == "SELL":
        profit = entry_price - price

        if profit <= -20 or row["ema9"] > row["ema21"]:
            trades.append(profit)
            current_day_loss += profit
            trade_count += 1
            print("EXIT SELL:", profit)
            position = None

    # ===== STOP DAY LOSS =====
    if current_day_loss <= daily_loss_limit:
        print("Daily loss limit hit")
        break

# ==============================
# RESULTS
# ==============================
total_profit = sum(trades)
total_trades = len(trades)
wins = len([t for t in trades if t > 0])

print("Total Trades:", total_trades)
print("Profit:", total_profit)

if total_trades > 0:
    print("Win Rate:", (wins / total_trades) * 100)
else:
    print("Win Rate: 0")

print("Backtest completed")
