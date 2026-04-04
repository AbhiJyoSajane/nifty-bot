import pandas as pd

# Load your file (make sure name matches exactly)
df = pd.read_csv("NIFTY 50.csv")

# 🔍 Print columns to debug (important)
print("Columns in file:", df.columns)

# ✅ Fix column names (Kaggle file usually has these)
df.columns = [col.strip().lower() for col in df.columns]

# Expected columns after this:
# date, open, high, low, close

# Convert date column
df['date'] = pd.to_datetime(df['date'])

# Sort properly
df = df.sort_values('date')

# Reset index
df = df.reset_index(drop=True)

# ===============================
# SIMPLE STRATEGY (EMA crossover)
# ===============================

df['ema20'] = df['close'].ewm(span=20).mean()
df['ema50'] = df['close'].ewm(span=50).mean()

# Buy/Sell signal
df['signal'] = 0
df.loc[df['ema20'] > df['ema50'], 'signal'] = 1
df.loc[df['ema20'] < df['ema50'], 'signal'] = -1

# Position (shifted signal)
df['position'] = df['signal'].shift()

# Returns
df['returns'] = df['close'].pct_change()

# Strategy returns
df['strategy_returns'] = df['returns'] * df['position']

# Cumulative P/L
df['cum_returns'] = (1 + df['strategy_returns']).cumprod()

# ===============================
# OUTPUT
# ===============================

print("\nLast rows:\n")
print(df.tail())

print("\nFinal Strategy Return:")
print(df['cum_returns'].iloc[-1])
