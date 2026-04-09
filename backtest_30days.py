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
MAX_TRADES_PER_DAY = 2

# ================= FETCH DATA =================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=30)

data = kite.historical_data(
    instrument_token=NIFTY,
    from_date=from_date,
    to_date=to_date,
    interval="5minute"
)

df = pd.DataFrame(data)
df.columns = [col.lower() for col in df.columns]

# ================= BACKTEST =================
position = None
entry_price = 0
sl_price = 0
target_price = 0
trail_price = 0

orb_high = None
orb_low = None

daily_pnl = 0
current_day = None
trade_count = 0

trades = []

for i in range(30, len(df)):

    row = df.iloc[i]
    prev = df.iloc[i-1]

    price = row['close']
    time = row['date'].time()
    date = row['date'].date()

    # ================= RESET DAILY =================
    if current_day != date:
        current_day = date
        daily_pnl = 0
        orb_high = None
        orb_low = None
        position = None
        trade_count = 0

    # ================= BUILD ORB =================
    if datetime.time(9,15) <= time <= datetime.time(9,45):

        if orb_high is None:
            orb_high = row['high']
            orb_low = row['low']
        else:
            orb_high = max(orb_high, row['high'])
            orb_low = min(orb_low, row['low'])

    # ================= SKIP IF ORB NOT READY =================
    if orb_high is None or orb_low is None:
        continue

    # ================= ORB FILTER =================
    if (orb_high - orb_low) < 40:
        continue

    # ================= TIME FILTER =================
    if time > datetime.time(13,30):
        continue

    # ================= ENTRY =================
    if position is None and time >= datetime.time(9,46) and daily_pnl > MAX_DAILY_LOSS and trade_count < MAX_TRADES_PER_DAY:

        # BUY
        if price > orb_high + 5 and prev['close'] > prev['open']:

            position = "BUY"
            entry_price = price

            sl_price = entry_price - (10 / PREMIUM_FACTOR)
            target_price = entry_price + (20 / PREMIUM_FACTOR)
            trail_price = sl_price

        # SELL
        elif price < orb_low - 5 and prev['close'] < prev['open']:

            position = "SELL"
            entry_price = price

            sl_price = entry_price + (10 / PREMIUM_FACTOR)
            target_price = entry_price - (20 / PREMIUM_FACTOR)
            trail_price = sl_price

    # ================= EXIT =================
    elif position:

        premium_move = (price - entry_price) * PREMIUM_FACTOR

        # ===== SMART TRAILING =====
        if position == "BUY":
            if price > entry_price + (15 / PREMIUM_FACTOR):
                trail_price = max(trail_price, price - (5 / PREMIUM_FACTOR))

        elif position == "SELL":
            if price < entry_price - (15 / PREMIUM_FACTOR):
                trail_price = min(trail_price, price + (5 / PREMIUM_FACTOR))

        exit_trade = False

        # BUY EXIT
        if position == "BUY":
            if price <= trail_price or price >= target_price:
                pnl = premium_move * LOT_SIZE
                exit_trade = True

        # SELL EXIT
        elif position == "SELL":
            if price >= trail_price or price <= target_price:
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

print("\n📊 FINAL OPTIMIZED ORB BACKTEST\n")

print(f"Starting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total PnL: ₹{round(capital - START_CAPITAL,2)}")

print(f"\nTotal Trades: {len(trades)}")
print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if len(trades) > 0:
    print(f"Win Rate: {round((wins/len(trades))*100,2)}%")
