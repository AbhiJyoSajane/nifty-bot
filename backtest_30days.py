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
PREMIUM_TARGET = 30
PREMIUM_SL = 15

START_CAPITAL = 20000
capital = START_CAPITAL

AVG_PREMIUM = 120
TRADE_CAPITAL = AVG_PREMIUM * LOT_SIZE

MAX_DAILY_LOSS = 2000
MAX_TRADES_PER_DAY = 5

# =========================
# TIME FILTER FUNCTION
# =========================
def in_trading_time(dt):
    t = dt.time()
    return (
        (datetime.time(9,30) <= t <= datetime.time(11,30)) or
        (datetime.time(13,45) <= t <= datetime.time(15,15))
    )

# =========================
# FETCH DATA
# =========================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=30)

data = kite.historical_data(
    instrument_token=NIFTY,
    from_date=from_date,
    to_date=to_date,
    interval="5minute"
)

df = pd.DataFrame(data)
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
entry_premium = 0

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

    # Reset daily
    if current_day != date:
        current_day = date
        daily_loss = 0
        daily_trades = 0

    # Time filter
    if not in_trading_time(dt):
        continue

    # Safety rules
    if daily_loss <= -MAX_DAILY_LOSS or daily_trades >= MAX_TRADES_PER_DAY:
        continue

    # ENTRY
    if position is None:

        if capital < TRADE_CAPITAL:
            continue

        # CE condition
        if (
            row['ema9'] > row['ema21'] and
            price > row['ema200'] and
            row['adx'] > 15 and
            row['close'] > row['open']
        ):
            position = "CE"
            entry_price = price
            entry_premium = AVG_PREMIUM
            capital -= TRADE_CAPITAL

        # PE condition
        elif (
            row['ema9'] < row['ema21'] and
            price < row['ema200'] and
            row['adx'] > 15 and
            row['close'] < row['open']
        ):
            position = "PE"
            entry_price = price
            entry_premium = AVG_PREMIUM
            capital -= TRADE_CAPITAL

    # EXIT
    elif position:

        nifty_move = price - entry_price
        premium_move = nifty_move * 0.5
        current_premium = entry_premium + premium_move

        # TARGET
        if current_premium >= entry_premium + PREMIUM_TARGET:
            pnl = PREMIUM_TARGET * LOT_SIZE
            capital += TRADE_CAPITAL + pnl
            total_pnl += pnl
            trades.append(pnl)

            daily_trades += 1
            position = None

        # STOP LOSS
        elif current_premium <= entry_premium - PREMIUM_SL:
            pnl = -PREMIUM_SL * LOT_SIZE
            capital += TRADE_CAPITAL + pnl
            total_pnl += pnl
            trades.append(pnl)

            daily_loss += pnl
            daily_trades += 1
            position = None

# =========================
# RESULT
# =========================
print("\n📊 HIGH WIN RATE STRATEGY BACKTEST\n")

print(f"Starting Capital: ₹{START_CAPITAL}")
print(f"Ending Capital: ₹{round(capital,2)}")
print(f"Total PnL: ₹{round(total_pnl,2)}")

print(f"\nTotal Trades: {len(trades)}")

wins = len([x for x in trades if x > 0])
losses = len([x for x in trades if x < 0])

print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")

if len(trades) > 0:
    print(f"Win Rate: {round((wins/len(trades))*100,2)}%")
