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
MAX_TRADES = 2
MAX_DAILY_LOSS = -2000

# ================= DATE =================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=30)

# ================= FETCH INDEX =================
spot = kite.historical_data(NIFTY, from_date, to_date, "5minute")
df = pd.DataFrame(spot)

if df.empty:
    print("❌ No data")
    exit()

df.columns = [c.lower() for c in df.columns]
df['ema20'] = df['close'].rolling(20).mean()

# ================= INSTRUMENTS =================
print("📥 Loading instruments...")
inst = pd.DataFrame(kite.instruments("NFO"))
inst['expiry'] = pd.to_datetime(inst['expiry'])

# ================= HELPERS =================
def get_expiry(date):
    return inst[(inst['name']=="NIFTY") & (inst['expiry']>=pd.to_datetime(date))]['expiry'].min()

# ================= OPTION CACHE =================
cache = {}

def load_option(token):
    if token not in cache:
        data = kite.historical_data(token, from_date, to_date, "5minute")
        df_opt = pd.DataFrame(data)

        if df_opt.empty:
            return None

        df_opt.columns = [c.lower() for c in df_opt.columns]
        df_opt['date'] = pd.to_datetime(df_opt['date'])
        df_opt.set_index('date', inplace=True)

        cache[token] = df_opt

    return cache[token]

def get_price(df_opt, time_):
    idx = df_opt.index.get_indexer([pd.to_datetime(time_)], method='nearest')
    return df_opt.iloc[idx[0]]['close']

# ================= 🔥 CORRECT STRIKE SELECTION =================
def get_best_token(price, expiry, opt_type, time_):

    atm = round(price / 50) * 50

    for diff in range(0, 500, 50):
        for direction in [1, -1]:

            strike = atm + (diff * direction)

            row = inst[
                (inst['name']=="NIFTY") &
                (inst['strike']==strike) &
                (inst['expiry']==expiry) &
                (inst['instrument_type']==opt_type)
            ]

            if row.empty:
                continue

            token = int(row.iloc[0]['instrument_token'])

            opt_df = load_option(token)
            if opt_df is None:
                continue

            entry_price = get_price(opt_df, time_)

            # ✅ STRICT CAPITAL CHECK
            if entry_price * LOT_SIZE <= capital:
                return token, strike

    return None, None

# ================= BACKTEST =================
position = None
entry_price = 0
entry_index = 0
sl_index = 0
target_index = 0
opt = None
strike = None
opt_type = None

orb_high = None
orb_low = None
pullback_flag = False

daily_pnl = 0
trades = 0
current_day = None

results = []
trade_log = []

for i in range(30, len(df)):

    row = df.iloc[i]
    prev = df.iloc[i-1]

    price = row['close']
    ema = row['ema20']
    time_ = row['date']
    t = time_.time()
    date = time_.date()

    # RESET DAILY
    if current_day != date:
        current_day = date
        orb_high = None
        orb_low = None
        position = None
        daily_pnl = 0
        trades = 0
        pullback_flag = False

    # ORB BUILD
    if datetime.time(9,15) <= t <= datetime.time(9,45):
        orb_high = max(orb_high or row['high'], row['high'])
        orb_low = min(orb_low or row['low'], row['low'])

    if orb_high is None:
        continue

    # ENTRY WINDOW
    if not (datetime.time(10,0) <= t <= datetime.time(11,30)):
        continue

    # BREAKOUT
    if price > orb_high:
        pullback_flag = "BUY"
    elif price < orb_low:
        pullback_flag = "SELL"

    # ENTRY
    if position is None and trades < MAX_TRADES and daily_pnl > MAX_DAILY_LOSS:

        expiry = get_expiry(date)
        if expiry is None:
            continue

        # CE BUY
        if pullback_flag == "BUY" and price > ema and prev['close'] < prev['open']:

            token, strike = get_best_token(price, expiry, "CE", time_)

            if token:
                opt = load_option(token)
                entry_price = get_price(opt, time_)
                entry_index = price
                position = "BUY"
                opt_type = "CE"

                sl_index = prev['low']
                risk = entry_index - sl_index
                target_index = entry_index + risk

        # PE BUY
        elif pullback_flag == "SELL" and price < ema and prev['close'] > prev['open']:

            token, strike = get_best_token(price, expiry, "PE", time_)

            if token:
                opt = load_option(token)
                entry_price = get_price(opt, time_)
                entry_index = price
                position = "SELL"
                opt_type = "PE"

                sl_index = prev['high']
                risk = sl_index - entry_index
                target_index = entry_index - risk

    # EXIT (INDEX BASED)
    elif position:

        current_index = price
        current_option = get_price(opt, time_)

        if current_index <= sl_index or current_index >= target_index:

            pnl = (current_option - entry_price) * LOT_SIZE

            trade_log.append({
                "date": date,
                "type": opt_type,
                "strike": strike,
                "entry": round(entry_price,2),
                "exit": round(current_option,2),
                "pnl": round(pnl,2)
            })

            capital += pnl
            daily_pnl += pnl
            results.append(pnl)

            position = None
            trades += 1

# ================= RESULT =================
wins = len([x for x in results if x > 0])
losses = len([x for x in results if x < 0])

print("\n📊 FINAL CLEAN RESULT\n")
print(f"Capital: ₹{round(capital,2)}")
print(f"PnL: ₹{round(capital - START_CAPITAL,2)}")
print(f"Trades: {len(results)} | Wins: {wins} | Losses: {losses}")

if results:
    print(f"Win Rate: {round((wins/len(results))*100,2)}%")

print("\n📋 TRADE DETAILS:\n")

for t in trade_log:
    print(f"{t['date']} | {t['type']} {t['strike']} | "
          f"{t['entry']} → {t['exit']} | PnL: ₹{t['pnl']}")
