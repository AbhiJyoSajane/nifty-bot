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
LOT_SIZE = 65

START_CAPITAL = 20000
capital = START_CAPITAL

AVG_PREMIUM = 120
TRADE_CAPITAL = AVG_PREMIUM * LOT_SIZE

MAX_DAILY_LOSS = 2000
MAX_TRADES_PER_DAY = 5

# =========================
# TIME FILTER
# =========================
def in_time(dt):
    t = dt.time()
    return (
        (datetime.time(9,30) <= t <= datetime.time(11,30)) or
        (datetime.time(13,45) <= t <= datetime.time(15,15))
    )

# =========================
# SUPERTREND FUNCTION
# =========================
def supertrend(df, period=10, multiplier=3):

    df['tr'] = df[['high','close']].max(axis=1) - df[['low','close']].min(axis=1)
    df['atr'] = df['tr'].rolling(period).mean()

    hl2 = (df['high'] + df['low']) / 2
    df['upperband'] = hl2 + multiplier * df['atr']
    df['lowerband'] = hl2 - multiplier * df['atr']

    df['supertrend'] = True

    for i in range(1, len(df)):
        if df['close'][i] > df['upperband'][i-1]:
            df.loc[i, 'supertrend'] = True
        elif df['close'][i] < df['lowerband'][i-1]:
            df.loc[i, 'supertrend'] = False
        else:
            df.loc[i, 'supertrend'] = df.loc[i-1, 'supertrend']

    return df

# =========================
# FETCH 5 MIN DATA
# =========================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=30)

data_5m = kite.historical_data(
    instrument_token=NIFTY,
    from_date=from_date,
    to_date=to_date,
    interval="5minute"
)

df5 = pd.DataFrame(data_5m)
df5.columns = [col.lower() for col in df5.columns]

# =========================
# FETCH 1 MIN DATA (SUPERTREND)
# =========================
data_1m = kite.historical_data(
    instrument_token=NIFTY,
    from_date=from_date,
    to_date=to_date,
    interval="minute"
)

df1 = pd.DataFrame(data_1m)
df1.columns = [col.lower() for col in df1.columns]

df1 = supertrend(df1)

# =========================
# MERGE 1m → 5m
# =========================
df1['date'] = pd.to_datetime(df1['date'])
df5['date'] = pd.to_datetime(df5['date'])

df1 = df1[['date', 'supertrend']]

df = pd.merge_asof(df5.sort_values('date'),
                   df1.sort_values('date'),
                   on='date',
                   direction='backward')

# =========================
# INDICATORS (5m)
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
entry_premium = 0

TARGET = 15
SL = 10

total_pnl = 0
trades = []

current_day = None
daily_loss = 0
daily_trades = 0

for i in range(1, len(df)):

    row = df.iloc[i]
    price = row['close']
    dt = row['date']
    date = dt.date()

    if current_day != date:
        current_day = date
        daily_loss = 0
        daily_trades = 0

    if not in_time(dt):
        continue

    if daily_loss <= -MAX_DAILY_LOSS or daily_trades >= MAX_TRADES_PER_DAY:
        continue

    # ENTRY
    if position is None:

        if capital < TRADE_CAPITAL:
            continue

        # CE
        if (
            row['ema9'] > row['ema21'] and
            price > row['ema200'] and
            row['adx'] > 10 and
            row['close'] > row['open'] and
            row['supertrend'] == True
        ):
            position = "CE"
            entry_price = price
            entry_premium = AVG_PREMIUM
            capital -= TRADE_CAPITAL

        # PE
        elif (
            row['ema9'] < row['ema21'] and
            price < row['ema200'] and
            row['adx'] > 10 and
            row['close'] < row['open'] and
            row['supertrend'] == False
        ):
            position = "PE"
            entry_price = price
            entry_premium = AVG_PREMIUM
            capital -= TRADE_CAPITAL

    # EXIT
    elif position:

        premium_move = (price - entry_price) * 0.5

        if premium_move >= TARGET:
            pnl = TARGET * LOT_SIZE
            capital += TRADE_CAPITAL + pnl
            total_pnl += pnl
            trades.append(pnl)

            daily_trades += 1
            position = None

        elif premium_move <= -SL:
            pnl = -SL * LOT_SIZE
            capital += TRADE_CAPITAL + pnl
            total_pnl += pnl
            trades.append(pnl)

            daily_loss += pnl
            daily_trades += 1
            position = None

# =========================
# RESULT
# =========================
real_pnl = capital - START_CAPITAL

print("\n📊 5m STRATEGY + 1m SUPERTREND\n")

print(f"Starting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total PnL: ₹{round(real_pnl,2)}")

print(f"\nTotal Trades: {len(trades)}")

wins = len([x for x in trades if x > 0])
losses = len([x for x in trades if x < 0])

print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if len(trades) > 0:
    print(f"Win Rate: {round((wins/len(trades))*100,2)}%")
