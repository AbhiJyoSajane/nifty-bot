import os
from kiteconnect import KiteConnect
import pandas as pd
from datetime import datetime, timedelta

# ==============================
# 🔑 ENV VARIABLES
# ==============================
API_KEY = os.environ.get("API_KEY")
API_SECRET = os.environ.get("API_SECRET")
REQUEST_TOKEN = os.environ.get("REQUEST_TOKEN")

kite = KiteConnect(api_key=API_KEY)
session = kite.generate_session(REQUEST_TOKEN, api_secret=API_SECRET)
kite.set_access_token(session["access_token"])

print("✅ Access Token Ready")

# ==============================
# 📊 FETCH NIFTY SPOT DATA
# ==============================
nifty_token = 256265

to_date = datetime.now()
from_date = to_date - timedelta(days=10)

spot_data = kite.historical_data(
    nifty_token,
    from_date,
    to_date,
    "5minute"
)

spot_df = pd.DataFrame(spot_data)

print("📊 Total candles:", len(spot_df))

if spot_df.empty:
    print("❌ No data fetched")
    exit()

# ==============================
# 📦 LOAD OPTION INSTRUMENTS
# ==============================
inst = pd.DataFrame(kite.instruments("NFO"))

nifty_opt = inst[
    (inst['name'] == 'NIFTY') &
    (inst['segment'] == 'NFO-OPT')
]

nearest_expiry = nifty_opt['expiry'].min()
nifty_opt = nifty_opt[nifty_opt['expiry'] == nearest_expiry]

print("✅ Loaded option instruments")

# ==============================
# 💰 CAPITAL
# ==============================
capital = 20000
qty = 65

position = None
entry_price = 0
trades = []

# ==============================
# ⚡ OPTION DATA CACHE (FIX)
# ==============================
option_cache = {}

# ==============================
# 🚀 MAIN LOOP
# ==============================
for i in range(1, len(spot_df)):

    print("Processing candle:", i)

    row = spot_df.iloc[i]
    prev = spot_df.iloc[i-1]

    price = row['close']
    timestamp = row['date']

    # ===== ATM STRIKE =====
    atm = round(price / 50) * 50

    call_row = nifty_opt[
        (nifty_opt['strike'] == atm) &
        (nifty_opt['instrument_type'] == 'CE')
    ]

    put_row = nifty_opt[
        (nifty_opt['strike'] == atm) &
        (nifty_opt['instrument_type'] == 'PE')
    ]

    if call_row.empty or put_row.empty:
        continue

    call_token = int(call_row.iloc[0]['instrument_token'])
    put_token = int(put_row.iloc[0]['instrument_token'])

    # ==============================
    # FETCH OPTION DATA ONLY ONCE
    # ==============================
    if call_token not in option_cache:
        print(f"📥 Fetching CALL data for {call_token}")
        call_data = kite.historical_data(call_token, from_date, to_date, "5minute")
        option_cache[call_token] = pd.DataFrame(call_data)

    if put_token not in option_cache:
        print(f"📥 Fetching PUT data for {put_token}")
        put_data = kite.historical_data(put_token, from_date, to_date, "5minute")
        option_cache[put_token] = pd.DataFrame(put_data)

    call_df = option_cache[call_token]
    put_df = option_cache[put_token]

    if call_df.empty or put_df.empty:
        continue

    # ==============================
    # MATCH NEAREST TIME (FIX)
    # ==============================
    call_df['diff'] = abs(call_df['date'] - timestamp)
    put_df['diff'] = abs(put_df['date'] - timestamp)

    call_price = call_df.sort_values('diff').iloc[0]['close']
    put_price = put_df.sort_values('diff').iloc[0]['close']

    # ==============================
    # ENTRY (STRICT VARSITY STYLE)
    # ==============================
    if position is None:

        # LONG CALL
        if row['close'] > prev['close']:
            position = "CALL"
            entry_price = call_price
            trades.append(("BUY CALL", timestamp, entry_price))

        # LONG PUT
        elif row['close'] < prev['close']:
            position = "PUT"
            entry_price = put_price
            trades.append(("BUY PUT", timestamp, entry_price))

    # ==============================
    # EXIT
    # ==============================
    elif position == "CALL":
        pnl = (call_price - entry_price) * qty

        if pnl >= 2000 or pnl <= -1000:
            capital += pnl
            trades.append(("EXIT CALL", timestamp, call_price, pnl))
            position = None

    elif position == "PUT":
        pnl = (entry_price - put_price) * qty

        if pnl >= 2000 or pnl <= -1000:
            capital += pnl
            trades.append(("EXIT PUT", timestamp, put_price, pnl))
            position = None

# ==============================
# 📊 RESULT
# ==============================
print("\n===== FINAL RESULT =====")
print("Final Capital:", capital)

exits = [t for t in trades if "EXIT" in t[0]]
wins = [t for t in exits if t[3] > 0]
losses = [t for t in exits if t[3] <= 0]

print("Trades:", len(exits))
print("Wins:", len(wins))
print("Losses:", len(losses))

if exits:
    print("Win Rate:", round(len(wins)/len(exits)*100, 2), "%")

print("\nSample Trades:")
for t in trades[:10]:
    print(t)
