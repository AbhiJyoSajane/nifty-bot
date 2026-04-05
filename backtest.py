import yfinance as yf
import pandas as pd

# ===== SETTINGS =====
LOT_SIZE = 50
TARGET = 10   # option premium ₹10
SL = 5        # option premium ₹5

DAILY_LOSS_LIMIT = -2000
MAX_TRADES_PER_DAY = 5

# =================== DATA ===================
def get_data():
    df = yf.download("^NSEI", interval="5m", period="30d")
    df.reset_index(inplace=True)

    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    df.columns = [col.lower() for col in df.columns]

    if 'datetime' not in df.columns:
        df.rename(columns={'date': 'datetime'}, inplace=True)

    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['datetime'].dt.date
    df['time'] = df['datetime'].dt.time

    return df


# =================== STRATEGY ===================
def run_strategy(df):

    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()
    df['ema200'] = df['close'].ewm(span=200).mean()

    total_profit = 0
    trades = []

    position = None
    entry_price = 0

    current_day = None
    day_high = 0
    day_low = 0

    daily_pnl = 0
    trade_count = 0

    for i in range(1, len(df)):

        row = df.iloc[i]
        dt = row['datetime']
        day = row['date']

        # NEW DAY RESET
        if current_day != day:
            current_day = day
            daily_pnl = 0
            trade_count = 0
            position = None

            # ORB range (first 15 min)
            day_data = df[df['date'] == day].iloc[:3]  # 3 candles = 15min
            if len(day_data) < 3:
                continue

            day_high = day_data['high'].max()
            day_low = day_data['low'].min()

        # RISK CONTROL
        if daily_pnl <= DAILY_LOSS_LIMIT or trade_count >= MAX_TRADES_PER_DAY:
            continue

        # ===== ENTRY =====
        if position is None:

            # ORB BREAKOUT + EMA FILTER
            if row['close'] > day_high and row['ema9'] > row['ema21'] and row['close'] > row['ema200']:
                position = "BUY"
                entry_price = row['close']

            elif row['close'] < day_low and row['ema9'] < row['ema21'] and row['close'] < row['ema200']:
                position = "SELL"
                entry_price = row['close']

            # BACKUP EMA CROSSOVER
            elif row['ema9'] > row['ema21'] and row['ema21'] > row['ema200']:
                position = "BUY"
                entry_price = row['close']

            elif row['ema9'] < row['ema21'] and row['ema21'] < row['ema200']:
                position = "SELL"
                entry_price = row['close']

        # ===== EXIT =====
        if position == "BUY":
            if row['close'] >= entry_price + 20:
                pnl = TARGET * LOT_SIZE
                trades.append(pnl)
                total_profit += pnl
                daily_pnl += pnl
                trade_count += 1
                position = None

            elif row['close'] <= entry_price - 10:
                pnl = -SL * LOT_SIZE
                trades.append(pnl)
                total_profit += pnl
                daily_pnl += pnl
                trade_count += 1
                position = None

        elif position == "SELL":
            if row['close'] <= entry_price - 20:
                pnl = TARGET * LOT_SIZE
                trades.append(pnl)
                total_profit += pnl
                daily_pnl += pnl
                trade_count += 1
                position = None

            elif row['close'] >= entry_price + 10:
                pnl = -SL * LOT_SIZE
                trades.append(pnl)
                total_profit += pnl
                daily_pnl += pnl
                trade_count += 1
                position = None

    # ===== RESULTS =====
    total_trades = len(trades)
    wins = len([t for t in trades if t > 0])
    losses = len([t for t in trades if t < 0])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    print("===== FINAL RESULT =====")
    print(f"Total Trades: {total_trades}")
    print(f"Winning Trades: {wins}")
    print(f"Losing Trades: {losses}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total Profit: ₹{total_profit}")


# =================== RUN ===================
df = get_data()
run_strategy(df)
