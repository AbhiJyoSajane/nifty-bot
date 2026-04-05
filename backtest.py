import yfinance as yf
import pandas as pd

# =========================
# FETCH DATA (5 MIN NIFTY)
# =========================
def get_data():
    df = yf.download("^NSEI", interval="5m", period="5d")

    df.reset_index(inplace=True)
    df.columns = [col.lower() for col in df.columns]

    df.rename(columns={"datetime": "datetime"}, inplace=True)

    df['datetime'] = pd.to_datetime(df['datetime'])
    
    return df


# =========================
# STRATEGY
# =========================
def run_strategy(df):

    # Indicators
    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()
    df['ema200'] = df['close'].ewm(span=200).mean()

    trades = []
    position = None
    entry_price = 0

    for i in range(1, len(df)):

        row = df.iloc[i]
        prev = df.iloc[i-1]

        # ===== BUY CONDITION =====
        if (
            prev['ema9'] < prev['ema21'] and
            row['ema9'] > row['ema21'] and
            row['close'] > row['ema200']
        ):
            position = "BUY"
            entry_price = row['close']

        # ===== SELL CONDITION =====
        elif (
            prev['ema9'] > prev['ema21'] and
            row['ema9'] < row['ema21'] and
            row['close'] < row['ema200']
        ):
            position = "SELL"
            entry_price = row['close']

        # ===== EXIT LOGIC =====
        if position == "BUY":
            if row['close'] >= entry_price + 40:
                trades.append(40)
                position = None
            elif row['close'] <= entry_price - 20:
                trades.append(-20)
                position = None

        elif position == "SELL":
            if row['close'] <= entry_price - 40:
                trades.append(40)
                position = None
            elif row['close'] >= entry_price + 20:
                trades.append(-20)
                position = None

    # ===== RESULTS =====
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
# MAIN
# =========================
df = get_data()
run_strategy(df)
