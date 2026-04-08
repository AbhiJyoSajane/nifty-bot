from kiteconnect import KiteConnect
import pandas as pd
import datetime
import os

# =========================
# CONFIG
# =========================
api_key = os.environ.get("API_KEY")
api_secret = os.environ.get("API_SECRET")
request_token = os.environ.get("REQUEST_TOKEN")

kite = KiteConnect(api_key=api_key)

data = kite.generate_session(request_token, api_secret=api_secret)
kite.set_access_token(data["access_token"])

print("✅ Connected")

# =========================
# DOWNLOAD INSTRUMENTS
# =========================
print("📥 Loading instruments...")

instruments = kite.instruments("NFO")
df_instr = pd.DataFrame(instruments)

# Filter only NIFTY options
df_instr = df_instr[df_instr['name'] == 'NIFTY']

# =========================
# SETTINGS
# =========================
NIFTY = 256265
TARGET = 30
SL = 15

# =========================
# GET EXPIRY
# =========================
def get_expiry(date):
    thursday = date + datetime.timedelta((3 - date.weekday()) % 7)
    return thursday

# =========================
# FETCH NIFTY DATA
# =========================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=5)

nifty_data = kite.historical_data(
    instrument_token=NIFTY,
    from_date=from_date,
    to_date=to_date,
    interval="5minute"
)

df = pd.DataFrame(nifty_data)
df.columns = [col.lower() for col in df.columns]

# =========================
# INDICATORS
# =========================
df['ema9'] = df['close'].ewm(span=9).mean()
df['ema21'] = df['close'].ewm(span=21).mean()
df['ema200'] = df['close'].ewm(span=200).mean()
df['adx'] = abs(df['ema9'] - df['ema21'])

# =========================
# BACKTEST
# =========================
position = None
entry_price = 0
total_pnl = 0
trades = []

for i in range(50, len(df)):

    row = df.iloc[i]
    price = row['close']
    date = row['date']

    strike = round(price / 50) * 50
    expiry = get_expiry(date.date())

    # Filter option instrument
    opt = df_instr[
        (df_instr['strike'] == strike) &
        (df_instr['expiry'] == pd.Timestamp(expiry))
    ]

    if opt.empty:
        continue

    # ================= ENTRY =================
    if position is None:

        if row['ema9'] > row['ema21'] and price > row['ema200'] and row['adx'] > 10:

            ce = opt[opt['instrument_type'] == 'CE']
            if ce.empty:
                continue

            token = ce.iloc[0]['instrument_token']

            option_data = kite.historical_data(
                instrument_token=token,
                from_date=date,
                to_date=date + datetime.timedelta(minutes=5),
                interval="5minute"
            )

            if not option_data:
                continue

            entry_price = option_data[0]['close']
            position = "CE"
            entry_time = date

        elif row['ema9'] < row['ema21'] and price < row['ema200'] and row['adx'] > 10:

            pe = opt[opt['instrument_type'] == 'PE']
            if pe.empty:
                continue

            token = pe.iloc[0]['instrument_token']

            option_data = kite.historical_data(
                instrument_token=token,
                from_date=date,
                to_date=date + datetime.timedelta(minutes=5),
                interval="5minute"
            )

            if not option_data:
                continue

            entry_price = option_data[0]['close']
            position = "PE"
            entry_time = date

    # ================= EXIT =================
    elif position:

        option_data = kite.historical_data(
            instrument_token=token,
            from_date=date,
            to_date=date + datetime.timedelta(minutes=5),
            interval="5minute"
        )

        if not option_data:
            continue

        current_price = option_data[0]['close']

        if current_price >= entry_price + TARGET:
            pnl = TARGET
            total_pnl += pnl
            trades.append(pnl)
            position = None

        elif current_price <= entry_price - SL:
            pnl = -SL
            total_pnl += pnl
            trades.append(pnl)
            position = None

# =========================
# RESULT
# =========================
print("\n📊 REAL OPTION BACKTEST RESULT\n")

print(f"Total Trades: {len(trades)}")
print(f"Total PnL: {total_pnl}")

wins = len([x for x in trades if x > 0])
losses = len([x for x in trades if x < 0])

print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if len(trades) > 0:
    print(f"Win Rate: {round((wins/len(trades))*100,2)}%")
