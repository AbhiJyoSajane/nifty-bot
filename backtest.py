import yfinance as yf
import pandas as pd

# =========================
# SETTINGS (REAL MONEY)
# =========================
CAPITAL = 20000
LOT_SIZE = 50

TARGET_POINTS = 60
SL_POINTS = 20

DAILY_TARGET = 3000
DAILY_LOSS = -2000

MAX_TRADES_PER_DAY = 10


# =========================
# FETCH DATA
# =========================
def get_data():
    df = yf.download("^NSEI", interval="5m", period="30d")

    df.reset_index(inplace=True)

    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    df.columns = [col.lower() for col in df.columns]

    if 'datetime' not in df.columns:
        df.rename(columns={'date': 'datetime'}, inplace=True)

    df['datetime'] = pd.to_datetime(df['datetime'])

    return df


# =========================
# STRATEGY
# =========================
def run_strategy(df):

    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()
    df['ema200'] = df['close'].ewm(span=200).mean()

    df['adx'] = abs(df['ema9'] - df['ema21'])

    position = None
    entry_price = 0

    total_profit = 0

    trades = []
    daily_pnl = 0
    trade_count = 0
    current_day = None

    for i in range(1, len(df)):

        row = df.iloc[i]
        dt = row['datetime']
        day = dt.date()

        # Reset daily values
        if current_day != day:
            current_day = day
            daily_pnl = 0
            trade_count = 0

        # STOP TRADING CONDITIONS
        if daily_pnl >= DAILY_TARGET or daily_pnl <= DAILY_LOSS or trade_count >= MAX_TRADES_PER_DAY:
            continue

        # ENTRY CONDITIONS
        if (
            position is None and
            row['ema9'] > row['ema21'] and
            row['close'] > row['ema200'] and
            row['adx'] > 10
        ):
            position = "BUY"
            entry_price = row['close']

        elif (
            position is None and
            row['ema9'] < row['ema21'] and
            row['close'] < row['ema200'] and
            row['adx'] > 10
        ):
            position = "SELL"
            entry_price = row['close']

        # EXIT LOGIC
        if position == "BUY":
            if row['close'] >= entry_price + TARGET_POINTS:
                pnl = TARGET_POINTS * LOT_SIZE
                trades.append(pnl)
                total_profit += pnl
                daily_pnl += pnl
                trade_count += 1
                position = None

            elif row['close'] <= entry_price - SL_POINTS:
                pnl = -SL_POINTS * LOT_SIZE
                trades.append(pnl)
                total_profit += pnl
                daily_pnl += pnl
                trade_count += 1
                position = None

        elif position == "SELL":
            if row['close'] <= entry_price - TARGET_POINTS:
                pnl = TARGET_POINTS * LOT_SIZE
                trades.append(pnl)
                total_profit += pnl
                daily_pnl += pnl
                trade_count += 1
                position = None

            elif row['close'] >= entry_price + SL_POINTS:
                pnl = -SL_POINTS * LOT_SIZE
                trades.append(pnl)
                total_profit += pnl
                daily_pnl += pnl
                trade_count += 1
                position = None

    # =========================
    # RESULT
    # =========================
    total_trades = len(trades)
    wins = len([t for t in trades if t > 0])
    losses = len([t for t in trades if t < 0])

    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    print("===== FINAL RESULT =====")
    print(f"Capital Used: ₹{CAPITAL}")
    print(f"Total Trades: {total_trades}")
    print(f"Winning Trades: {wins}")
    print(f"Losing Trades: {losses}")
    print(f"Win Rate: {win_rate:.2f} %")
    print(f"Total Profit: ₹{total_profit}")


# =========================
# RUN
# =========================
df = get_data()
run_strategy(df)
