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

MAX_TRADES = 2
MAX_DAILY_LOSS = -2000

# ================= DATE =================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=30)

# ================= FETCH INDEX =================
spot = kite.historical_data(NIFTY, from_date, to_date, "5minute")
df = pd.DataFrame(spot)
df.columns = [c.lower() for c in df.columns]

# ================= INSTRUMENTS =================
inst = pd.DataFrame(kite.instruments("NFO"))
inst['expiry'] = pd.to_datetime(inst['expiry'])

# ================= HELPERS =================
def get_atm(price):
    return round(price / 50) * 50

def get_expiry(date):
    return inst[(inst['name']=="NIFTY") & (inst['expiry']>=pd.to_datetime(date))]['expiry'].min()

def find_best_option(price, expiry, opt_type, time_):
    atm = get_atm(price)

    for diff in range(-300, 300, 50):
        strike = atm + diff
        row = inst[
            (inst['name']=="NIFTY") &
            (inst['strike']==strike) &
            (inst['expiry']==expiry) &
            (inst['instrument_type']==opt_type)
        ]

        if not row.empty:
            token = int(row.iloc[0]['instrument_token'])
            data = kite.historical_data(token, from_date, to_date, "5minute")

            df_opt = pd.DataFrame(data)
            if df_opt.empty:
                continue

            df_opt['date'] = pd.to_datetime(df_opt['date'])
            df_opt.set_index('date', inplace=True)

            idx = df_opt.index.get_indexer([pd.to_datetime(time_)], method='nearest')
            premium = df_opt.iloc[idx[0]]['close']

            if 80 <= premium <= 150:
                return token, df_opt

    return None, None

def get_price(opt_df, time_):
    idx = opt_df.index.get_indexer([pd.to_datetime(time_)], method='nearest')
    return opt_df.iloc[idx[0]]['close']

# ================= BACKTEST =================
position = None
entry_price = 0
sl = 0
opt_df = None

orb_high = None
orb_low = None

daily_pnl = 0
trades = 0
current_day = None

results = []

for i in range(30, len(df)):

    row = df.iloc[i]
    prev = df.iloc[i-1]

    price = row['close']
    time_ = row['date']
    t = time_.time()
    date = time_.date()

    # RESET
    if current_day != date:
        current_day = date
        orb_high = None
        orb_low = None
        position = None
        daily_pnl = 0
        trades = 0

    # BUILD ORB
    if datetime.time(9,15) <= t <= datetime.time(9,45):
        orb_high = max(orb_high or row['high'], row['high'])
        orb_low = min(orb_low or row['low'], row['low'])

    if orb_high is None:
        continue

    # ENTRY WINDOW
    if not (datetime.time(9,50) <= t <= datetime.time(10,45)):
        continue

    # ENTRY
    if position is None and trades < MAX_TRADES and daily_pnl > MAX_DAILY_LOSS:

        expiry = get_expiry(date)

        # BUY
        if price > orb_high and (price - orb_high) > 10:

            token, opt_df = find_best_option(price, expiry, "CE", time_)
            if opt_df is not None:
                entry_price = get_price(opt_df, time_)
                position = "BUY"
                sl = entry_price - 20

        # SELL
        elif price < orb_low and (orb_low - price) > 10:

            token, opt_df = find_best_option(price, expiry, "PE", time_)
            if opt_df is not None:
                entry_price = get_price(opt_df, time_)
                position = "SELL"
                sl = entry_price - 20

    # EXIT (TRAILING)
    elif position:

        current = get_price(opt_df, time_)

        profit = current - entry_price

        # TRAILING LOGIC
        if profit > 20:
            sl = entry_price

        if profit > 40:
            sl = entry_price + 20

        if profit > 60:
            sl = entry_price + 40

        if current <= sl:
            pnl = (current - entry_price) * LOT_SIZE

            capital += pnl
            daily_pnl += pnl
            results.append(pnl)

            position = None
            trades += 1

# ================= RESULT =================
wins = len([x for x in results if x > 0])
losses = len([x for x in results if x < 0])

print("\n📊 PRO OPTION RESULT\n")

print(f"Starting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total PnL: ₹{round(capital - START_CAPITAL,2)}")

print(f"\nTrades: {len(results)} | Wins: {wins} | Losses: {losses}")

if results:
    print(f"Win Rate: {round((wins/len(results))*100,2)}%")
