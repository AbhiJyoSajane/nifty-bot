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
from_date = to_date - timedelta(days=7)

spot_data = kite.historical_data(
    nifty_token,
    from_date,
    to_date,
    "5minute"
)

spot_df = pd.DataFrame(spot_data)

# ==============================
# 📈 INDICATORS (VARSITY)
# ==============================
spot_df['EMA9'] = spot_df['close'].ewm(span=9).mean()

spot_df['cum_vol'] = spot_df['volume'].cumsum()
spot_df['cum_vol_price'] = (spot_df['close'] * spot_df['volume']).cumsum()
spot_df['VWAP'] = spot_df['cum_vol_price'] / spot_df['cum_vol']

# ==============================
# 📦 LOAD INSTRUMENTS
# ==============================
inst = pd.DataFrame(kite.instruments("NFO"))

nifty_opt = inst[
    (inst['name'] == 'NIFTY') &
    (inst['segment'] == 'NFO-OPT')
]

nearest_expiry = nifty_opt['expiry'].min()
nifty_opt = nifty_opt[nifty_opt['expiry'] == nearest_expiry]

# ==============================
# 💰 CAPITAL SETUP
# ==============================
capital = 20000
risk_per_trade = 1200
max_daily_loss = 2400

position = None
entry_price = 0
qty = 65
daily_loss = 0

trades = []

# Cache for option data (important optimization)
option_cache = {}

# ==============================
# 🚀 MAIN LOOP
# ==============================
for i in range(20, len(spot_df)):

    if daily_loss >= max_daily_loss:
        print("🚫 Daily SL hit")
        break

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

    # ===== FETCH OPTION DATA (CACHE) =====
    if call_token not in option_cache:
        call_data = kite.historical_data(
            call_token, from_date, to_date, "5minute"
        )
        option_cache[call_token] = pd.DataFrame(call_data)

    if put_token not in option_cache:
        put_data = kite.historical_data(
            put_token, from_date, to_date, "5minute"
        )
        option_cache[put_token] = pd.DataFrame(put_data)

    call_df = option_cache[call_token]
    put_df = option_cache[put_token]

    # ===== SYNC TIMESTAMP =====
    call_row_data = call_df[call_df['date'] == timestamp]
    put_row_data = put_df[put_df['date'] == timestamp]

    if call_row_data.empty or put_row_data.empty:
        continue

    call_price = call_row_data.iloc[0]['close']
    put_price = put_row_data.iloc[0]['close']

    # ===== VOLATILITY FILTER =====
    candle_range = row['high'] - row['low']
    avg_range = spot_df['high'].rolling(10).mean().iloc[i]
    strong_candle = candle_range > avg_range

    # ==============================
    # ENTRY
    # ==============================
    if position is None:

        # CALL BUY
        if (
            row['close'] > row['VWAP'] and
            row['EMA9'] > row['VWAP'] and
            row['high'] > prev['high'] and
            strong_candle
        ):
            position = "CALL"
            entry_price = call_price
            trades.append(("BUY CALL", timestamp, entry_price))

        # PUT BUY
        elif (
            row['close'] < row['VWAP'] and
            row['EMA9'] < row['VWAP'] and
            row['low'] < prev['low'] and
            strong_candle
        ):
            position = "PUT"
            entry_price = put_price
            trades.append(("BUY PUT", timestamp, entry_price))

    # ==============================
    # EXIT
    # ==============================
    elif position == "CALL":
        pnl = (call_price - entry_price) * qty

        if pnl <= -risk_per_trade or pnl >= 2 * risk_per_trade:
            capital += pnl
            trades.append(("EXIT CALL", timestamp, call_price, pnl))

            if pnl < 0:
                daily_loss += abs(pnl)

            position = None

    elif position == "PUT":
        pnl = (entry_price - put_price) * qty

        if pnl <= -risk_per_trade or pnl >= 2 * risk_per_trade:
            capital += pnl
            trades.append(("EXIT PUT", timestamp, put_price, pnl))

            if pnl < 0:
                daily_loss += abs(pnl)

            position = None

# ==============================
# 📊 RESULTS
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
