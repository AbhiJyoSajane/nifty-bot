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
MAX_TRADES_PER_DAY = 3

# ================= DATE RANGE =================
from_date = datetime.datetime(2026,1,1)
to_date = datetime.datetime(2026,1,31)

# ================= FETCH DATA =================
data = kite.historical_data(
    instrument_token=NIFTY,
    from_date=from_date,
    to_date=to_date,
    interval="5minute"
)

df = pd.DataFrame(data)
df.columns = [col.lower() for col in df.columns]

# ================= VARIABLES =================
position = None
entry_price = 0
sl_price = 0
target_price = 0

orb_high = None
orb_low = None

crb_high = None
crb_low = None

daily_pnl = 0
current_day = None
trade_count = 0

crb_trade_taken = False

trades = []

# ================= LOOP =================
for i in range(30, len(df)):

    row = df.iloc[i]
    prev = df.iloc[i-1]

    price = row['close']
    time = row['date'].time()
    date = row['date'].date()

    # RESET DAILY
    if current_day != date:
        current_day = date
        daily_pnl = 0
        orb_high = None
        orb_low = None
        crb_high = None
        crb_low = None
        position = None
        trade_count = 0
        crb_trade_taken = False

    # ================= ORB BUILD =================
    if datetime.time(9,15) <= time <= datetime.time(9,45):
        if orb_high is None:
            orb_high = row['high']
            orb_low = row['low']
        else:
            orb_high = max(orb_high, row['high'])
            orb_low = min(orb_low, row['low'])

    # ================= CRB BUILD =================
    if datetime.time(14,30) <= time <= datetime.time(15,0):
        if crb_high is None:
            crb_high = row['high']
            crb_low = row['low']
        else:
            crb_high = max(crb_high, row['high'])
            crb_low = min(crb_low, row['low'])

    # ================= ENTRY =================
    if position is None and daily_pnl > MAX_DAILY_LOSS and trade_count < MAX_TRADES_PER_DAY:

        # ===== MORNING ORB =====
        if datetime.time(9,46) <= time <= datetime.time(11,30):

            if orb_high and price > orb_high and prev['close'] > prev['open']:
                position = "BUY"
                entry_price = price
                sl_price = prev['low']
                risk = entry_price - sl_price
                target_price = entry_price + (2 * risk)

            elif orb_low and price < orb_low and prev['close'] < prev['open']:
                position = "SELL"
                entry_price = price
                sl_price = prev['high']
                risk = sl_price - entry_price
                target_price = entry_price - (2 * risk)

        # ===== EVENING CRB =====
        elif datetime.time(15,0) <= time <= datetime.time(15,20) and not crb_trade_taken:

            buffer = 3

            if crb_high and price > crb_high + buffer and prev['close'] > prev['open']:
                position = "BUY"
                entry_price = price
                sl_price = crb_low
                risk = entry_price - sl_price
                target_price = entry_price + (2 * risk)
                crb_trade_taken = True

            elif crb_low and price < crb_low - buffer and prev['close'] < prev['open']:
                position = "SELL"
                entry_price = price
                sl_price = crb_high
                risk = sl_price - entry_price
                target_price = entry_price - (2 * risk)
                crb_trade_taken = True

    # ================= EXIT =================
    elif position:

        premium_move = (price - entry_price) * PREMIUM_FACTOR
        exit_trade = False

        if position == "BUY":
            if price <= sl_price or price >= target_price:
                pnl = premium_move * LOT_SIZE
                exit_trade = True

        elif position == "SELL":
            if price >= sl_price or price <= target_price:
                pnl = premium_move * LOT_SIZE
                exit_trade = True

        if exit_trade:
            capital += pnl
            daily_pnl += pnl
            trades.append(pnl)
            position = None
            trade_count += 1

# ================= RESULT =================
wins = len([x for x in trades if x > 0])
losses = len([x for x in trades if x < 0])
total_pnl = round(capital - START_CAPITAL, 2)

print("\n📊 FINAL ORB + CRB (SAFE DUAL STRATEGY)\n")

print(f"Starting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total PnL: ₹{total_pnl}")

print(f"\nTotal Trades: {len(trades)}")
print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if len(trades) > 0:
    print(f"Win Rate: {round((wins/len(trades))*100,2)}%")
