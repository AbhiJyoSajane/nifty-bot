from kiteconnect import KiteConnect
import pandas as pd
import datetime
import os

# ================= CONFIG =================
api_key = os.environ.get("API_KEY")
api_secret = os.environ.get("API_SECRET")
request_token = os.environ.get("REQUEST_TOKEN")

kite = KiteConnect(api_key=api_key)
data = kite.generate_session(request_token, api_secret=api_secret)
kite.set_access_token(data["access_token"])

print("✅ Connected")

# ================= SETTINGS =================
NIFTY = 256265

START_CAPITAL = 20000
capital = START_CAPITAL

MAX_TRADES = 5
MAX_DAILY_LOSS = -2000

# ================= FETCH DATA =================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=30)

data = kite.historical_data(NIFTY, from_date, to_date, "5minute")
df = pd.DataFrame(data)

if df.empty:
    print("❌ No data")
    exit()

df.columns = [c.lower() for c in df.columns]

# ================= SUPERTREND =================
def supertrend(df, period=10, multiplier=3):
    df['hl2'] = (df['high'] + df['low']) / 2
    df['tr'] = df['high'] - df['low']
    df['atr'] = df['tr'].rolling(period).mean()

    df['upperband'] = df['hl2'] + multiplier * df['atr']
    df['lowerband'] = df['hl2'] - multiplier * df['atr']

    st = [0]*len(df)
    trend = [True]*len(df)

    for i in range(1, len(df)):
        if df['close'][i] > df['upperband'][i-1]:
            trend[i] = True
        elif df['close'][i] < df['lowerband'][i-1]:
            trend[i] = False
        else:
            trend[i] = trend[i-1]

        st[i] = df['lowerband'][i] if trend[i] else df['upperband'][i]

    df['supertrend'] = st
    df['trend'] = trend

    return df

df = supertrend(df)

# ================= BACKTEST =================
position = None
entry_price = 0

total_points = 0
wins = 0
losses = 0
trade_count = 0

daily_pnl = 0
daily_trades = 0
current_day = None

for i in range(20, len(df)):

    row = df.iloc[i]
    price = row['close']
    st = row['supertrend']
    date = row['date'].date()

    # ===== RESET DAILY =====
    if current_day != date:
        current_day = date
        daily_pnl = 0
        daily_trades = 0
        position = None

    # ===== LIMITS =====
    if daily_trades >= MAX_TRADES:
        continue

    if daily_pnl <= MAX_DAILY_LOSS:
        continue

    # ===== ENTRY =====
    if position is None:

        # BUY
        if row['trend'] == True and price > st:
            position = "BUY"
            entry_price = price

        # SELL
        elif row['trend'] == False and price < st:
            position = "SELL"
            entry_price = price

    # ===== EXIT =====
    elif position:

        exit_trade = False

        # BUY EXIT
        if position == "BUY" and price < st:
            pnl = price - entry_price
            exit_trade = True

        # SELL EXIT
        elif position == "SELL" and price > st:
            pnl = entry_price - price
            exit_trade = True

        if exit_trade:
            total_points += pnl
            capital += pnl
            daily_pnl += pnl

            if pnl > 0:
                wins += 1
            else:
                losses += 1

            trade_count += 1
            daily_trades += 1

            position = None

# ================= RESULT =================
print("\n📊 SUPERTREND CLEAN STRATEGY\n")

print(f"Starting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total Points: {round(total_points,2)}")

print(f"\nTrades: {trade_count}")
print(f"Wins: {wins} | Losses: {losses}")

if trade_count > 0:
    print(f"Win Rate: {round((wins/trade_count)*100,2)}%")
else:
    print("No trades")
