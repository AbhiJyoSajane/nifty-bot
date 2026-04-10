from kiteconnect import KiteConnect
import pandas as pd
import datetime
import os

# ================= CONFIG =================
api_key = os.environ.get("API_KEY")
api_secret = os.environ.get("API_SECRET")
request_token = os.environ.get("REQUEST_TOKEN")

kite = KiteConnect(api_key=api_key)

# ===== GENERATE ACCESS TOKEN (RUN ONCE) =====
data = kite.generate_session(request_token, api_secret=api_secret)
kite.set_access_token(data["access_token"])

print("✅ Connected")

# ================= SETTINGS =================
NIFTY = 256265
LOT_SIZE = 65

START_CAPITAL = 20000
capital = START_CAPITAL

MAX_DAILY_LOSS = -2000
MAX_TRADES = 3

PREMIUM_FACTOR = 0.5  # Approx premium move

# ================= DATE =================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=30)

# ================= FETCH DATA =================
spot = kite.historical_data(NIFTY, from_date, to_date, "5minute")
df = pd.DataFrame(spot)
df.columns = [c.lower() for c in df.columns]

# ================= HELPER =================
def get_atm(price):
    return round(price / 50) * 50

# ================= BACKTEST =================
position = None
entry_price = 0
sl = 0

orb_high = None
orb_low = None

daily_pnl = 0
trade_count = 0
current_day = None

trades = []

for i in range(20, len(df)):

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

    # ===== SKIP NOISE TIME =====
    if time < datetime.time(10,0):
        continue

    # ===== ENTRY CONDITIONS =====
    if position is None and daily_pnl > MAX_DAILY_LOSS and trade_count < MAX_TRADES:

        candle_body = abs(row['close'] - row['open'])
        candle_range = row['high'] - row['low']

        strong_candle = candle_body > (0.6 * candle_range)

        # ===== BUY CE =====
        if price > orb_high and prev['close'] > prev['open'] and strong_candle:

            # RETEST LOGIC
            if df.iloc[i-2]['close'] < orb_high:
                continue

            position = "BUY"
            entry_price = price
            sl = prev['low']

        # ===== BUY PE =====
        elif price < orb_low and prev['close'] < prev['open'] and strong_candle:

            if df.iloc[i-2]['close'] > orb_low:
                continue

            position = "SELL"
            entry_price = price
            sl = prev['high']

    # ===== EXIT =====
    elif position:

        move = (price - entry_price) * PREMIUM_FACTOR

        # TRAILING SL
        if move > 15:
            sl = entry_price

        if move > 30:
            if position == "BUY":
                sl = max(sl, entry_price + 10)
            else:
                sl = min(sl, entry_price - 10)

        exit_trade = False

        if position == "BUY":
            if price <= sl:
                pnl = (price - entry_price) * PREMIUM_FACTOR * LOT_SIZE
                exit_trade = True

        elif position == "SELL":
            if price >= sl:
                pnl = (entry_price - price) * PREMIUM_FACTOR * LOT_SIZE
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
