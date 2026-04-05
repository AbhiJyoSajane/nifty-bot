import yfinance as yf
import pandas as pd

# =========================
# FETCH DATA (30 DAYS)
# =========================
def get_data():
    df = yf.download("^NSEI", interval="5m", period="30d")

    df.reset_index(inplace=True)

    # Fix tuple columns issue
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    df.columns = [col.lower() for col in df.columns]

    # Ensure datetime column
    if 'datetime' not in df.columns:
        df.rename(columns={'date': 'datetime'}, inplace=True)

    df['datetime'] = pd.to_datetime(df['datetime'])

    return df


# =========================
# STRATEGY (WITH FILTER)
# =========================
def run_strategy(df):

    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()
    df['ema200'] = df['close'].ewm(span=200).mean()

    # Simple trend strength (ADX-like filter)
    df['adx'] = abs(df['ema9'] - df['ema21'])

    trades = []
    position = None
    entry_price = 0

    TARGET = 60
    SL = 20

    for i in range(1, len(df)):

        row = df.iloc[i]

        # BUY (with filter)
        if (
            position is None and
            row['ema9'] > row['ema21'] and
            row['close'] > row['ema200'] and
            row['adx'] > 10
        ):
            position = "BUY"
            entry_price = row['close']

        # SELL (with filter)
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
            if row['close'] >= entry_price + TARGET:
                trades.append(TARGET)
                position = None
            elif row['close'] <= entry_price - SL:
                trades.append(-SL)
                position = None

        elif position == "SELL":
            if row['close'] <= entry_price - TARGET:
                trades.append(TARGET)
                position = None
            elif row['close'] >= entry_price + SL:
                trades.append(-SL)
                position = None

    # =========================
    # RESULT
    # =========================
    total_trades = len(trades)
    wins = len([t for t in trades if t > 0])
    losses = len([t for t in trades if t < 0])

    total_profit = sum(trades)
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    print("===== FINAL RESULT =====")
    print(f"Total Trades: {total_trades}")
    print(f"Winning Trades: {wins}")
    print(f"Losing Trades: {losses}")
    print(f"Win Rate: {win_rate:.2f} %")
    print(f"Total Profit: {total_profit}")


# =========================
# RUN
# =========================
df = get_data()
run_strategy(df)
