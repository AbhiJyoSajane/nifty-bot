import os
import pandas as pd
from datetime import datetime, timedelta
from kiteconnect import KiteConnect

# ==============================
# ENV VARIABLES (Railway)
# ==============================
API_KEY = os.environ.get("API_KEY")
API_SECRET = os.environ.get("API_SECRET")
REQUEST_TOKEN = os.environ.get("REQUEST_TOKEN")

# ==============================
# SESSION GENERATION
# ==============================
kite = KiteConnect(api_key=API_KEY)

session = kite.generate_session(REQUEST_TOKEN, api_secret=API_SECRET)
kite.set_access_token(session["access_token"])

print("✅ Access Token Generated")

# ==============================
# CONFIG
# ==============================
NIFTY_TOKEN = 256265
LOT_SIZE = 65

capital = 20000
risk_per_trade = 1200
target_per_trade = 2400

# ==============================
# FETCH DATA
# ==============================
to_date = datetime.now()
from_date = to_date - timedelta(days=7)

spot_data = kite.historical_data(
    NIFTY_TOKEN,
    from_date,
    to_date,
    "5minute"
)

spot_df = pd.DataFrame(spot_data)

print("📊 Total candles:", len(spot_df))

# ==============================
# LOAD OPTION INSTRUMENTS
# ==============================
inst = pd.DataFrame(kite.instruments("NFO"))

nifty_opt = inst[
    (inst['name'] == 'NIFTY') &
    (inst['segment'] == 'NFO-OPT')
]

nearest_expiry = nifty_opt['expiry'].min()
nifty_opt = nifty_opt[nifty_opt['expiry'] == nearest_expiry]

# ==============================
# CACHE
# ==============================
option_cache = {}

# ==============================
# BACKTEST VARIABLES
# ==============================
position = None
entry_price = 0
option_type = None

trades = []

# ==============================
# MAIN LOOP
# ==============================
for i in range(2, len(spot_df)):

    row = spot_df.iloc[i]
    prev = spot_df.iloc[i-1]

    price = row['close']
    timestamp = row['date']

    # ATM STRIKE
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

    # FETCH OPTION DATA (CACHE)
    if call_token not in option_cache:
        call_data = kite.historical_data(call_token, from_date, to_date, "5minute")
        option_cache[call_token] = pd.DataFrame(call_data)

    if put_token not in option_cache:
        put_data = kite.historical_data(put_token, from_date, to_date, "5minute")
        option_cache[put_token] = pd.DataFrame(put_data)

    call_df = option_cache[call_token]
    put_df = option_cache[put_token]

    if call_df.empty or put_df.empty:
        continue

    # MATCH TIME (nearest)
    call_df['diff'] = abs(call_df['date'] - timestamp)
    put_df['diff'] = abs(put_df['date'] - timestamp)

    call_price = call_df.sort_values('diff').iloc[0]['close']
    put_price = put_df.sort_values('diff').iloc[0]['close']

    # ==============================
    # ENTRY
    # ==============================
    if position is None:

        # CALL BUY
        if row['close'] > prev['high']:
            position = "CALL"
            entry_price = call_price
            option_type = "CE"
            trades.append(("BUY CALL", timestamp, entry_price))

        # PUT BUY
        elif row['close'] < prev['low']:
            position = "PUT"
            entry_price = put_price
            option_type = "PE"
            trades.append(("BUY PUT", timestamp, entry_price))

    # ==============================
    # EXIT
    # ==============================
    elif position == "CALL":

        pnl = (call_price - entry_price) * LOT_SIZE

        if pnl <= -risk_per_trade or pnl >= target_per_trade:
            capital += pnl
            trades.append(("EXIT CALL", timestamp, call_price, pnl))
            position = None

    elif position == "PUT":

        pnl = (entry_price - put_price) * LOT_SIZE

        if pnl <= -risk_per_trade or pnl >= target_per_trade:
            capital += pnl
            trades.append(("EXIT PUT", timestamp, put_price, pnl))
            position = None

# ==============================
# RESULT
# ==============================
print("\n===== BACKTEST RESULT =====")
print("Final Capital:", capital)

exits = [t for t in trades if "EXIT" in t[0]]
wins = [t for t in exits if t[3] > 0]
losses = [t for t in exits if t[3] <= 0]

print("Total Trades:", len(exits))
print("Wins:", len(wins))
print("Losses:", len(losses))

if exits:
    print("Win Rate:", round(len(wins)/len(exits)*100, 2), "%")

print("\nSample Trades:")
for t in trades[:10]:
    print(t)
