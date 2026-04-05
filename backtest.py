import yfinance as yf
import pandas as pd

# ========= SETTINGS =========
SYMBOL = "^NSEI"
INTERVAL = "5m"
PERIOD = "60d"

LOT_SIZE = 50
MAX_TRADES = 5
MAX_DAILY_LOSS = -2000

# ========= DATA =========
def get_data():
    df = yf.download(SYMBOL, interval=INTERVAL, period=PERIOD, auto_adjust=True, progress=False)

    if df is None or df.empty:
        raise Exception("No data fetched")

    # Fix columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    df.columns = [str(c).lower() for c in df.columns]

    print("COLUMNS:", df.columns)

    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
    elif 'date' in df.columns:
        df['datetime'] = pd.to_datetime(df['date'])
    else:
        raise Exception("No datetime column found")

    df.set_index('datetime', inplace=True)

    return df


# ========= STRATEGY =========
def apply_strategy(df):

    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()

    df['date'] = df.index.date

    trades = []

    grouped = df.groupby('date')

    for date, day in grouped:

        day = day.copy()

        if len(day) < 5:
            continue

        daily_pnl = 0
        trades_today = 0

        # ORB (first 15 min)
        orb_high = day.iloc[:3]['high'].max()
        orb_low = day.iloc[:3]['low'].min()

        position = None
        entry = 0
        sl = 0
        target = 0

        for i in range(3, len(day)):

            row = day.iloc[i]

            if trades_today >= MAX_TRADES:
                break

            if daily_pnl <= MAX_DAILY_LOSS:
                break

            # ENTRY
            if position is None:

                # LONG
                if row['close'] > orb_high and row['ema9'] > row['ema21']:
                    position = 'LONG'
                    entry = row['close']
                    sl = orb_low
                    target = entry + (entry - sl) * 2
                    trades_today += 1

                # SHORT
                elif row['close'] < orb_low and row['ema9'] < row['ema21']:
                    position = 'SHORT'
                    entry = row['close']
                    sl = orb_high
                    target = entry - (sl - entry) * 2
                    trades_today += 1

            # EXIT
            elif position == 'LONG':

                if row['low'] <= sl:
                    pnl = (sl - entry) * LOT_SIZE
                    trades.append(pnl)
                    daily_pnl += pnl
                    position = None

                elif row['high'] >= target:
                    pnl = (target - entry) * LOT_SIZE
                    trades.append(pnl)
                    daily_pnl += pnl
                    position = None

            elif position == 'SHORT':

                if row['high'] >= sl:
                    pnl = (entry - sl) * LOT_SIZE
                    trades.append(pnl)
                    daily_pnl += pnl
                    position = None

                elif row['low'] <= target:
                    pnl = (entry - target) * LOT_SIZE
                    trades.append(pnl)
                    daily_pnl += pnl
                    position = None

    return trades


# ========= RUN =========
df = get_data()
trades = apply_strategy(df)

# ========= RESULT =========
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
