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

orb_high = None
orb_low = None

confirm_high = None
confirm_low = None
confirm_bull = False
confirm_bear = False

trades = []

for i in range(30, len(df)):

    row = df.iloc[i]
    prev = df.iloc[i-1]

    price = row['close']
    time = row['date'].time()

    # ================= RESET DAILY =================
    if time >= datetime.time(9,15) and time < datetime.time(9,20):
        orb_high = None
        orb_low = None
        confirm_high = None
        confirm_low = None
        position = None

    # ================= BUILD ORB =================
    if datetime.time(9,15) <= time <= datetime.time(9,30):

        if orb_high is None:
            orb_high = row['high']
            orb_low = row['low']
        else:
            orb_high = max(orb_high, row['high'])
            orb_low = min(orb_low, row['low'])

    # ================= CONFIRMATION CANDLE (9:30–9:35) =================
    if time == datetime.time(9,35):

        confirm_high = prev['high']
        confirm_low = prev['low']

        confirm_bull = prev['close'] > prev['open']
        confirm_bear = prev['close'] < prev['open']

    # ================= VOLUME =================
    avg_vol = df['volume'].rolling(20).mean().iloc[i]
    high_vol = row['volume'] > avg_vol * 1.2

    # ================= ENTRY =================
    if position is None and time > datetime.time(9,35):

        # BUY
        if (
            orb_high is not None and
            price > orb_high and
            confirm_bull and
            high_vol
        ):
            position = "BUY"
            entry_price = price

            sl_price = confirm_low
            risk = entry_price - sl_price
            target_price = entry_price + (2 * risk)

        # SELL
        elif (
            orb_low is not None and
            price < orb_low and
            confirm_bear and
            high_vol
        ):
            position = "SELL"
            entry_price = price

            sl_price = confirm_high
            risk = sl_price - entry_price
            target_price = entry_price - (2 * risk)

    # ================= EXIT =================
    elif position:

        premium_move = (price - entry_price) * PREMIUM_FACTOR

        # BUY
        if position == "BUY":

            if price <= sl_price or price >= target_price:
                pnl = premium_move * LOT_SIZE
                capital += pnl
                trades.append(pnl)
                position = None

            else:
                # TRAILING
                sl_price = max(sl_price, prev['low'])

        # SELL
        elif position == "SELL":

            if price >= sl_price or price <= target_price:
                pnl = premium_move * LOT_SIZE
                capital += pnl
                trades.append(pnl)
                position = None

            else:
                # TRAILING
                sl_price = min(sl_price, prev['high'])

# ================= RESULT =================
wins = len([x for x in trades if x > 0])
losses = len([x for x in trades if x < 0])

print("\n📊 STRICT ORB (CONFIRMATION + RR + TRAILING)\n")

print(f"Starting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total PnL: ₹{round(capital - START_CAPITAL,2)}")

print(f"\nTotal Trades: {len(trades)}")
print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if len(trades) > 0:
    print(f"Win Rate: {round((wins/len(trades))*100,2)}%")
