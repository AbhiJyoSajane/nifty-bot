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
LOT_SIZE = 50

START_CAPITAL = 20000
capital = START_CAPITAL

MAX_TRADES = 3
MAX_DAILY_LOSS = -2000

# Premium SL/Target
SL_POINTS = 20
TARGET_POINTS = 40

# ================= DATE =================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=30)

# ================= FETCH INDEX =================
spot = kite.historical_data(NIFTY, from_date, to_date, "5minute")
df = pd.DataFrame(spot)

if df.empty:
    print("❌ No index data")
    exit()

df.columns = [c.lower() for c in df.columns]

# ================= LOAD INSTRUMENTS =================
print("📥 Loading instruments...")
inst = pd.DataFrame(kite.instruments("NFO"))
inst['expiry'] = pd.to_datetime(inst['expiry'])

# ================= HELPERS =================
def get_atm(price):
    return round(price / 50) * 50

def get_expiry(date):
    valid = inst[
        (inst['name'] == "NIFTY") &
        (inst['expiry'] >= pd.to_datetime(date))
    ]
    return valid['expiry'].min() if not valid.empty else None

def get_token(strike, expiry, opt_type):
    row = inst[
        (inst['name'] == "NIFTY") &
        (inst['strike'] == strike) &
        (inst['expiry'] == expiry) &
        (inst['instrument_type'] == opt_type)
    ]
    return int(row.iloc[0]['instrument_token']) if not row.empty else None

# ================= OPTION CACHE =================
option_cache = {}

def load_option(token):
    if token not in option_cache:
        data = kite.historical_data(token, from_date, to_date, "5minute")
        df_opt = pd.DataFrame(data)

        if df_opt.empty:
            return None

        df_opt.columns = [c.lower() for c in df_opt.columns]
        df_opt['date'] = pd.to_datetime(df_opt['date'])
        df_opt.set_index('date', inplace=True)

        option_cache[token] = df_opt

    return option_cache[token]

def get_price(opt_df, time_):
    time_ = pd.to_datetime(time_)
    idx = opt_df.index.get_indexer([time_], method='nearest')
    return opt_df.iloc[idx[0]]['close']

# ================= BACKTEST =================
position = None
entry_price = 0
sl = 0
target = 0
opt_df = None

orb_high = None
orb_low = None

daily_pnl = 0
trade_count = 0
current_day = None

results = []

for i in range(30, len(df)):

    row = df.iloc[i]
    prev = df.iloc[i-1]

    price = row['close']
    time_ = row['date']
    t = time_.time()
    date = time_.date()

    # ===== RESET DAILY =====
    if current_day != date:
        current_day = date
        orb_high = None
        orb_low = None
        position = None
        daily_pnl = 0
        trade_count = 0

    # ===== BUILD ORB =====
    if datetime.time(9,15) <= t <= datetime.time(9,45):
        if orb_high is None:
            orb_high = row['high']
            orb_low = row['low']
        else:
            orb_high = max(orb_high, row['high'])
            orb_low = min(orb_low, row['low'])

    if orb_high is None:
        continue

    # ===== ENTRY WINDOW =====
    if not (datetime.time(9,46) <= t <= datetime.time(11,30)):
        continue

    # ===== ENTRY =====
    if position is None and trade_count < MAX_TRADES and daily_pnl > MAX_DAILY_LOSS:

        expiry = get_expiry(date)
        if expiry is None:
            continue

        atm = get_atm(price)

        # BUY SIGNAL
        if price > orb_high and prev['close'] > prev['open']:

            strike = atm - 100
            token = get_token(strike, expiry, "CE")

            if token:
                opt_df = load_option(token)
                if opt_df is None:
                    continue

                entry_price = get_price(opt_df, time_)
                position = "BUY"

                sl = entry_price - SL_POINTS
                target = entry_price + TARGET_POINTS

        # SELL SIGNAL
        elif price < orb_low and prev['close'] < prev['open']:

            strike = atm + 100
            token = get_token(strike, expiry, "PE")

            if token:
                opt_df = load_option(token)
                if opt_df is None:
                    continue

                entry_price = get_price(opt_df, time_)
                position = "SELL"

                sl = entry_price - SL_POINTS
                target = entry_price + TARGET_POINTS

    # ===== EXIT =====
    elif position:

        current = get_price(opt_df, time_)

        if current <= sl or current >= target:

            pnl = (current - entry_price) * LOT_SIZE

            capital += pnl
            daily_pnl += pnl
            results.append(pnl)

            position = None
            trade_count += 1

# ================= RESULT =================
wins = len([x for x in results if x > 0])
losses = len([x for x in results if x < 0])

print("\n📊 FINAL OPTION BACKTEST\n")

print(f"Starting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total PnL: ₹{round(capital - START_CAPITAL,2)}")

print(f"\nTrades: {len(results)}")
print(f"Wins: {wins} | Losses: {losses}")

if results:
    print(f"Win Rate: {round((wins/len(results))*100,2)}%")
else:
    print("No trades executed")
