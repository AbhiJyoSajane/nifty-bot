import yfinance as yf
import pandas as pd
import numpy as np

# ================= SETTINGS =================
SYMBOL = "^NSEI"
INTERVAL = "5m"
PERIOD = "60d"

MAX_TRADES = 5
MAX_DAILY_LOSS = -2000
LOT_SIZE = 50

# ================= FETCH DATA =================
def get_data():
    df = yf.download(SYMBOL, interval=INTERVAL, period=PERIOD, auto_adjust=True)

    # Fix index / datetime issues
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()

    # Normalize column names
    df.columns = [str(col).lower() for col in df.columns]

    # Handle datetime safely
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
    elif 'date' in df.columns:
        df['datetime'] = pd.to_datetime(df['date'])
    elif 'index' in df.columns:
        df['datetime'] = pd.to_datetime(df['index'])
    else:
        raise Exception("No datetime column found")

    df.set_index('datetime', inplace=True)

    return df


# ================= STRATEGY =================
def apply_strategy(df):

    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()

    df['date'] = df.index.date

    trades = []
    daily_pnl = {}
    trade_count = {}

    grouped = df.groupby('date')

    prev_day_high = None
    prev_day_low = None

    for date, day in grouped:

        day = day.copy()

        daily_pnl[date] = 0
        trade_count[date] = 0

        # Weekly levels
        week_data = df[df.index.date <= date].last('5D')
        week_high = week_data['high'].max()
        week_low = week_data['low'].min()

        # ORB (first 15 min)
        if len(day) < 5:
            continue

        orb_high = day.iloc[:3]['high'].max()
        orb_low = day.iloc[:3]['low'].min()

        position = None
        entry_price = 0

        for i in range(3, len(day)):

            row = day.iloc[i]

            if trade_count[date] >= MAX_TRADES:
                break

            if daily_pnl[date] <= MAX_DAILY_LOSS:
                break

            # ===== ENTRY =====
            if position is None:

                # ORB breakout + EMA
                if row['close'] > orb_high and row['ema9'] > row['ema21']:
                    position = 'LONG'
                    entry_price = row['close']
                    trade_count[date] += 1

                elif row['close'] < orb_low and row['ema9'] < row['ema21']:
                    position = 'SHORT'
                    entry_price = row['close']
                    trade_count[date] += 1

                # EMA backup
                elif row['ema9'] > row['ema21']:
                    position = 'LONG'
                    entry_price = row['close']
                    trade_count[date] += 1

                elif row['ema9'] < row['ema21']:
                    position = 'SHORT'
                    entry_price = row['close']
                    trade_count[date] += 1

            # ===== EXIT =====
            elif position == 'LONG':

                if row['ema9'] < row['ema21']:
                    pnl = (row['close'] - entry_price) * LOT_SIZE
                    daily_pnl[date] += pnl
                    trades.append(pnl)
                    position = None

            elif position == 'SHORT':

                if row['ema9'] > row['ema21']:
                    pnl = (entry_price - row['close']) * LOT_SIZE
                    daily_pnl[date] += pnl
                    trades.append(pnl)
                    position = None

        # Store previous day levels
        prev_day_high = day['high'].max()
        prev_day_low = day['low'].min()

    return trades


# ================= RUN =================
df = get_data()
trades = apply_strategy(df)

# ================= RESULT =================
total_trades = len(trades)
winning = len([t for t in trades if t > 0])
losing = len([t for t in trades if t < 0])
total_profit = sum(trades)

print("\n===== FINAL RESULT =====")
print("Total Trades:", total_trades)
print("Winning Trades:", winning)
print("Losing Trades:", losing)
print("Win Rate:", (winning / total_trades * 100) if total_trades > 0 else 0, "%")
print("Total Profit:", total_profit)
