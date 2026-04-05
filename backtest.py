import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ==============================
# SETTINGS
# ==============================
SYMBOL = "^NSEI"
INTERVAL = "5m"
DAYS = 5

MAX_DAILY_LOSS = 2000
MAX_TRADES = 5

# ==============================
# FETCH DATA FROM INTERNET
# ==============================
def get_data():
    df = yf.download(
        SYMBOL,
        interval=INTERVAL,
        period=f"{DAYS}d",
        progress=False
    )

    if df.empty:
        raise Exception("No data fetched")

    df.reset_index(inplace=True)

    # Standard column naming
    df.rename(columns={
        "Datetime": "datetime",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close"
    }, inplace=True)

    return df

# ==============================
# STRATEGY
# ==============================
def run_strategy(df):

    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()

    total_profit = 0
    trades = 0
    wins = 0
    losses = 0

    current_day = None
    day_loss = 0

    for i in range(30, len(df)):

        row = df.iloc[i]
        prev = df.iloc[i-1]

        day = row['datetime'].date()

        # Reset daily
        if current_day != day:
            current_day = day
            day_loss = 0
            trades = 0

        # Stop trading if limits hit
        if day_loss <= -MAX_DAILY_LOSS or trades >= MAX_TRADES:
            continue

        price = row['close']

        # ORB (first 15 min = first 3 candles)
        if i < 3:
            continue

        orb_high = df.iloc[i-3:i]['high'].max()
        orb_low = df.iloc[i-3:i]['low'].min()

        # ==============================
        # BUY CONDITION
        # ==============================
        if price > orb_high and row['ema9'] > row['ema21']:

            entry = price
            target = entry + 50
            sl = entry - 25

        # ==============================
        # SELL CONDITION
        # ==============================
        elif price < orb_low and row['ema9'] < row['ema21']:

            entry = price
            target = entry - 50
            sl = entry + 25

        else:
            continue

        # Simulate exit next candle
        next_candle = df.iloc[i+1]

        exit_price = next_candle['close']

        pnl = exit_price - entry if entry < target else entry - exit_price

        total_profit += pnl
        trades += 1

        if pnl > 0:
            wins += 1
        else:
            losses += 1
            day_loss += pnl

    # ==============================
    # RESULT
    # ==============================
    print("\n===== FINAL RESULT =====")
    print("Total Trades:", trades)
    print("Winning Trades:", wins)
    print("Losing Trades:", losses)

    winrate = (wins / trades * 100) if trades > 0 else 0
    print("Win Rate:", round(winrate, 2), "%")
    print("Total Profit:", round(total_profit, 2))


# ==============================
# MAIN
# ==============================
df = get_data()
run_strategy(df)
