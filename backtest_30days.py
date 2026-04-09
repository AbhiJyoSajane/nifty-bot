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
LOT_SIZE = 50
START_CAPITAL = 20000
capital = START_CAPITAL

MAX_DAILY_LOSS = -2000
MAX_TRADES = 3

# ================= LOAD INSTRUMENTS =================
inst = pd.DataFrame(kite.instruments("NFO"))
inst['expiry'] = pd.to_datetime(inst['expiry'])

def get_atm(price):
    return round(price / 50) * 50

def get_expiry(date):
    return inst[(inst['name']=="NIFTY") & (inst['expiry']>=pd.to_datetime(date))]['expiry'].min()

def get_token(strike, expiry, opt_type):
    row = inst[
        (inst['name']=="NIFTY") &
        (inst['strike']==strike) &
        (inst['expiry']==expiry) &
        (inst['instrument_type']==opt_type)
    ]
    if not row.empty:
        return int(row.iloc[0]['instrument_token'])
    return None

# ================= FETCH SPOT =================
NIFTY = 256265
from_date = datetime.datetime(2026,1,1)
to_date = datetime.datetime(2026,1,31)

spot = kite.historical_data(NIFTY, from_date, to_date, "5minute")
spot_df = pd.DataFrame(spot)
spot_df.columns = [c.lower() for c in spot_df.columns]

# ================= OPTION CACHE =================
option_cache = {}

def load_option(token):
    if token not in option_cache:
        data = kite.historical_data(token, from_date, to_date, "5minute")
        df = pd.DataFrame(data)
        df.columns = [c.lower() for c in df.columns]
        df.set_index('date', inplace=True)
        option_cache[token] = df
    return option_cache[token]

# ================= VARIABLES =================
orb_high = None
orb_low = None

position = None
entry_price = 0
opt_df = None

spot_sl = None  # 🔥 candle SL based on spot

daily_pnl = 0
trade_count = 0
current_day = None

trades = []

# ================= LOOP =================
for i in range(30, len(spot_df)):

    row = spot_df.iloc[i]
    prev = spot_df.iloc[i-1]

    price = row['close']
    time = row['date']
    t = time.time()
    date = time.date()

    # RESET DAILY
    if current_day != date:
        current_day = date
        orb_high = None
        orb_low = None
        position = None
        trade_count = 0
        daily_pnl = 0

    # BUILD ORB
    if datetime.time(9,15) <= t <= datetime.time(9,45):
        if orb_high is None:
            orb_high = row['high']
            orb_low = row['low']
        else:
            orb_high = max(orb_high, row['high'])
            orb_low = min(orb_low, row['low'])

    if orb_high is None:
        continue

    # ================= ENTRY =================
    if position is None and daily_pnl > MAX_DAILY_LOSS and trade_count < MAX_TRADES:

        if datetime.time(9,46) <= t <= datetime.time(11,30):

            expiry = get_expiry(date)
            atm = get_atm(price)

            # BUY CE
            if price > orb_high and prev['close'] > prev['open']:

                token = get_token(atm, expiry, "CE")
                if token:
                    opt_df = load_option(token)

                    if time in opt_df.index:
                        premium = opt_df.loc[time]['close']

                        position = "CE"
                        entry_price = premium
                        spot_sl = prev['low']   # 🔥 candle SL

            # BUY PE
            elif price < orb_low and prev['close'] < prev['open']:

                token = get_token(atm, expiry, "PE")
                if token:
                    opt_df = load_option(token)

                    if time in opt_df.index:
                        premium = opt_df.loc[time]['close']

                        position = "PE"
                        entry_price = premium
                        spot_sl = prev['high']  # 🔥 candle SL

    # ================= EXIT =================
    elif position and opt_df is not None:

        if time in opt_df.index:
            premium = opt_df.loc[time]['close']

            exit_trade = False

            # 🔥 SPOT BASED SL
            if position == "CE" and price <= spot_sl:
                exit_trade = True

            elif position == "PE" and price >= spot_sl:
                exit_trade = True

            # 🔼 TRAILING (OPTION BASED)
            move = premium - entry_price

            if move > 20:
                spot_sl = entry_price  # breakeven shift

            # EXIT
            if exit_trade:
                pnl = (premium - entry_price) * LOT_SIZE
                capital += pnl
                daily_pnl += pnl
                trades.append(pnl)
                position = None
                trade_count += 1

# ================= RESULT =================
wins = len([x for x in trades if x > 0])
losses = len([x for x in trades if x < 0])

print("\n📊 FINAL OPTION ORB (CANDLE SL + DAILY SL)\n")
print(f"Starting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total PnL: ₹{round(capital - START_CAPITAL,2)}")

print(f"\nTrades: {len(trades)} | Wins: {wins} | Losses: {losses}")
if trades:
    print(f"Win Rate: {round((wins/len(trades))*100,2)}%")
