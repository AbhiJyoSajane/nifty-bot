import pandas as pd

# ===============================
# LOAD DATA
# ===============================

df = pd.read_csv("NIFTY 50.csv")

# Clean column names
df.columns = [col.strip().lower() for col in df.columns]

print("Columns in file:", df.columns)

# Convert date
df['date'] = pd.to_datetime(df['date'])

# Sort data
df = df.sort_values('date').reset_index(drop=True)

# ===============================
# STRATEGY (EMA Crossover)
# ===============================

df['ema20'] = df['close'].ewm(span=20).mean()
df['ema50'] = df['close'].ewm(span=50).mean()

# Signal: 1 = Buy, -1 = Sell
df['signal'] = 0
df.loc[df['ema20'] > df['ema50'], 'signal'] = 1
df.loc[df['ema20'] < df['ema50'], 'signal'] = -1

# Position (shift signal)
df['position'] = df['signal'].shift()

# Returns
df['returns'] = df['close'].pct_change()

# Strategy returns
df['strategy_returns'] = df['returns'] * df['position']

# Cumulative returns
df['cum_returns'] = (1 + df['strategy_returns']).cumprod()

# ===============================
# OUTPUT
# ===============================

print("\n==== LAST 5 ROWS ====\n")
print(df[['date','close','ema20','ema50','signal','cum_returns']].tail())

print("\n==== FINAL RESULT ====\n")
print("Final Return:", df['cum_returns'].iloc[-1])
