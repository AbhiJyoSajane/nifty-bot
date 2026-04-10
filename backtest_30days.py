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

MAX_DAILY_LOSS = -2000
MAX_TRADES = 3

# ================= DATE =================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=30)

# ================= FETCH SPOT =================
spot = kite.historical_data(NIFTY, from_date, to_date, "5minute")
df = pd.DataFrame(spot)
df.columns = [c.lower() for c in df.columns]

# ================= LOAD INSTRUMENTS =================
print("📥 Loading instruments...")
inst_df = pd.DataFrame(kite.instruments("NFO"))
inst_df['expiry'] = pd.to_datetime(inst_df['expiry'])

# ================= HELPERS =================
def get_atm(price):
    return round(price / 50) * 50

def get_expiry(date):
    valid = inst_df[
        (inst_df['name'] == "NIFTY") &
        (inst_df['expiry'] >= pd.to_datetime(date))
    ]
    return valid['expiry'].min()

def get_option_token(strike, expiry, opt_type):
    row = inst_df[
        (inst_df['name'] == "NIFTY") &
        (inst_df['strike'] == strike) &
        (inst_df['expiry'] == expiry) &
        (inst_df['instrument_type'] == opt_type)
    ]
    return int(row.iloc[0]['instrument_token']) if not row.empty else None

# ================= OPTION CACHE =================
option_cache = {}

def load_option(token):
    if token not in option_cache:
        data = kite.historical_data(token, from_date, to_date, "5minute")
        df_opt = pd.DataFrame(data)
        df_opt.columns = [c.lower() for c in df_opt.columns]
        df_opt['date'] = pd.to_datetime(df_opt['date'])
        df_opt.set_index('date', inplace=True)
        option_cache[token] = df_opt
    return option_cache[token]

def get_nearest_price(opt_df, time_):
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

trades = []

for i in range(20, len(df)):

    row = df.iloc[i]
    prev = df.iloc[i-1]

    price = row['close']
    time_ = row['date']
    t = time_.time()
    date = time_.date()

    # ===== RESET DAILY =====
    if current_day != date:
        current_day = date
        daily_pnl = 0
        trade_count = 0
        orb_high = None
        orb_low = None
        position = None

    # ===== BUILD ORB =====
    if datetime.time(9,15) <= t <= datetime.time(9,45):
        if orb_high is None:
            orb_high = row['high']
            orb_low = row['low']
        else:
            orb_high = max(orb_high, row['high'])
            orb_low = min(orb_low, row['low'])

    if orb_high is None or orb_low is None:
        continue

    # ===== ENTRY =====
    if position is None and daily_pnl > MAX_DAILY_LOSS and trade_count < MAX_TRADES:

        strike = get_atm(price)
        expiry = get_expiry(date)

        # BUY CE
        if price > orb_high and prev['close'] > prev['open']:

            token = get_option_token(strike, expiry, "CE")
            if token is None:
                continue

            opt_df = load_option(token)
            entry_price = get_nearest_price(opt_df, time_)

            position = "CE"
            sl = entry_price - 15
            target = entry_price + 30

        # BUY PE
        elif price < orb_low and prev['close'] < prev['open']:

            token = get_option_token(strike, expiry, "PE")
            if token is None:
                continue

            opt_df = load_option(token)
            entry_price = get_nearest_price(opt_df, time_)

            position = "PE"
            sl = entry_price - 15
            target = entry_price + 30

    # ===== EXIT =====
    elif position:

        current_price = get_nearest_price(opt_df, time_)

        exit_trade = False

        if current_price <= sl or current_price >= target:
            pnl = (current_price - entry_price) * LOT_SIZE
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

print("\n📊 REAL OPTION BACKTEST RESULT\n")

print(f"Starting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total PnL: ₹{round(capital - START_CAPITAL,2)}")

print(f"\nTotal Trades: {len(trades)}")
print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if len(trades) > 0:
    print(f"Win Rate: {round((wins/len(trades))*100,2)}%")
