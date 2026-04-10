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
LOT_SIZE = 65

START_CAPITAL = 20000
capital = START_CAPITAL

PREMIUM_FACTOR = 0.5

MAX_DAILY_LOSS = -2000
MAX_TRADES = 10   # 🔥 more trades = more points

# ================= DATE =================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=30)

# ================= FETCH DATA =================
data = kite.historical_data(NIFTY, from_date, to_date, "5minute")
df = pd.DataFrame(data)
df.columns = [col.lower() for col in df.columns]

# ================= BACKTEST =================
position = None
entry_price = 0
sl = 0
target = 0

orb_high = None
orb_low = None

daily_pnl = 0
trade_count = 0
current_day = None

total_points = 0
trades = []

for i in range(30, len(df)):

    row = df.iloc[i]
    prev = df.iloc[i-1]

    price = row['close']
    time = row['date'].time()
    date = row['date'].date()

    # ===== RESET DAILY =====
    if current_day != date:
        current_day = date
        daily_pnl = 0
        trade_count = 0
        orb_high = None
        orb_low = None
        position = None

    # ===== BUILD ORB =====
    if datetime.time(9,15) <= time <= datetime.time(9,45):

        if orb_high is None:
            orb_high = row['high']
            orb_low = row['low']
        else:
            orb_high = max(orb_high, row['high'])
            orb_low = min(orb_low, row['low'])

    if orb_high is None or orb_low is None:
        continue

    # ===== FULL DAY TRADING =====
    if datetime.time(9,46) <= time <= datetime.time(15,10):

        # ===== ENTRY (RELAXED) =====
        if position is None and daily_pnl > MAX_DAILY_LOSS and trade_count < MAX_TRADES:

            # BUY
            if price > orb_high:

                position = "BUY"
                entry_price = price

                sl = prev['low']
                risk = entry_price - sl
                target = entry_price + (2 * risk)

            # SELL
            elif price < orb_low:

                position = "SELL"
                entry_price = price

                sl = prev['high']
                risk = sl - entry_price
                target = entry_price - (2 * risk)

        # ===== EXIT =====
        elif position:

            exit_trade = False

            if position == "BUY":
                if price <= sl or price >= target:
                    pnl = (price - entry_price) * PREMIUM_FACTOR * LOT_SIZE
                    points = price - entry_price
                    exit_trade = True

            elif position == "SELL":
                if price >= sl or price <= target:
                    pnl = (entry_price - price) * PREMIUM_FACTOR * LOT_SIZE
                    points = entry_price - price
                    exit_trade = True

            if exit_trade:
                capital += pnl
                daily_pnl += pnl
                trades.append(pnl)

                total_points += points

                position = None
                trade_count += 1

# ================= RESULT =================
wins = len([x for x in trades if x > 0])
losses = len([x for x in trades if x < 0])

print("\n📊 AGGRESSIVE ORB (MAX POINT CAPTURE)\n")

print(f"Total Points Captured: {round(total_points,2)}")

print(f"\nStarting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total PnL: ₹{round(capital - START_CAPITAL,2)}")

print(f"\nTotal Trades: {len(trades)}")
print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if trades:
    print(f"Win Rate: {round((wins/len(trades))*100,2)}%")
