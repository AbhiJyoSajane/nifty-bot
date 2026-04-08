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
# SETTINGS
# =========================
NIFTY = 256265
TARGET = 30
SL = 15

# =========================
# EXPIRY FUNCTION
# =========================
def get_expiry(date):
    thursday = date + datetime.timedelta((3 - date.weekday()) % 7)
    return thursday.strftime("%d%b").upper()

# =========================
# FETCH NIFTY DATA
# =========================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=10)

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

for i in range(10, len(df)):

    row = df.iloc[i]
    price = row['close']
    date = row['date']

    strike = round(price / 50) * 50
    expiry = get_expiry(date.date())

    # ENTRY
    if position is None:

        if row['ema9'] > row['ema21'] and price > row['ema200'] and row['adx'] > 10:

            symbol = f"NFO:NIFTY{expiry}{int(strike)}CE"

            try:
                quote = kite.ltp([symbol])
                entry_price = quote[symbol]['last_price']
                position = "CE"
                entry_time = date
            except:
                continue

        elif row['ema9'] < row['ema21'] and price < row['ema200'] and row['adx'] > 10:

            symbol = f"NFO:NIFTY{expiry}{int(strike)}PE"

            try:
                quote = kite.ltp([symbol])
                entry_price = quote[symbol]['last_price']
                position = "PE"
                entry_time = date
            except:
                continue

    # EXIT
    elif position:

        try:
            quote = kite.ltp([symbol])
            current_price = quote[symbol]['last_price']
        except:
            continue

        if current_price >= entry_price + TARGET:
            pnl = TARGET
            total_pnl += pnl

            trades.append((entry_time, date, position, pnl))
            position = None

        elif current_price <= entry_price - SL:
            pnl = -SL
            total_pnl += pnl

            trades.append((entry_time, date, position, pnl))
            position = None

# =========================
# RESULT
# =========================
print("\n📊 OPTION BACKTEST RESULT\n")

print(f"Total Trades: {len(trades)}")
print(f"Total PnL: {total_pnl}")

wins = len([t for t in trades if t[3] > 0])
losses = len([t for t in trades if t[3] < 0])

print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if len(trades) > 0:
    win_rate = (wins / len(trades)) * 100
    print(f"Win Rate: {round(win_rate,2)}%")
