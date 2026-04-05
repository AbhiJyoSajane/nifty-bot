import yfinance as yf
import pandas as pd

# ==============================
# FETCH DATA
# ==============================
def get_data():
    df = yf.download("^NSEI", interval="5m", period="60d")
    df.reset_index(inplace=True)
    df.rename(columns={
        "Datetime": "datetime",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    }, inplace=True)

    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['datetime'].dt.date
    return df


# ==============================
# ADD INDICATORS
# ==============================
def add_indicators(df):
    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()

    # Yesterday High Low
    df['y_high'] = df.groupby('date')['high'].transform('max').shift(1)
    df['y_low'] = df.groupby('date')['low'].transform('min').shift(1)

    # Weekly High Low
    df['week'] = df['datetime'].dt.isocalendar().week
    df['w_high'] = df.groupby('week')['high'].transform('max')
    df['w_low'] = df.groupby('week')['low'].transform('min')

    return df


# ==============================
# BACKTEST LOGIC
# ==============================
def backtest(df):
    trades = 0
    wins = 0
    losses = 0
    total_profit = 0

    current_day = None
    day_loss = 0
    trade_count = 0

    orb_high = 0
    orb_low = 0

    for i in range(1, len(df)):

        row = df.iloc[i]
        prev = df.iloc[i-1]

        # New day reset
        if current_day != row['date']:
            current_day = row['date']
            day_loss = 0
            trade_count = 0

            # ORB calculation (first 15 min)
            day_data = df[df['date'] == current_day].head(3)
            if len(day_data) >= 3:
                orb_high = day_data['high'].max()
                orb_low = day_data['low'].min()

        # Stop trading if limits hit
        if trade_count >= 5 or day_loss <= -2000:
            continue

        price = row['close']

        # ======================
        # ENTRY CONDITIONS
        # ======================

        buy_signal = (
            price > orb_high and
            row['ema9'] > row['ema21'] and
            price > row['y_high']
        )

        sell_signal = (
            price < orb_low and
            row['ema9'] < row['ema21'] and
            price < row['y_low']
        )

        # Backup EMA crossover
        ema_buy = prev['ema9'] < prev['ema21'] and row['ema9'] > row['ema21']
        ema_sell = prev['ema9'] > prev['ema21'] and row['ema9'] < row['ema21']

        # ======================
        # EXECUTION
        # ======================

        if buy_signal or ema_buy:
            entry = price
            sl = entry - 20
            target = entry + 40

        elif sell_signal or ema_sell:
            entry = price
            sl = entry + 20
            target = entry - 40

        else:
            continue

        # Simulate next candle exit
        next_row = df.iloc[i+1] if i+1 < len(df) else row

        exit_price = next_row['close']
        profit = exit_price - entry if entry < exit_price else entry - exit_price

        # Track stats
        trades += 1
        trade_count += 1

        if profit > 0:
            wins += 1
        else:
            losses += 1
            day_loss += profit

        total_profit += profit

    # ======================
    # FINAL RESULT
    # ======================
    print("===== FINAL RESULT =====")
    print(f"Total Trades: {trades}")
    print(f"Winning Trades: {wins}")
    print(f"Losing Trades: {losses}")
    print(f"Win Rate: {round((wins/trades)*100,2) if trades else 0} %")
    print(f"Total Profit: {round(total_profit,2)}")


# ==============================
# RUN
# ==============================
df = get_data()
df = add_indicators(df)
backtest(df)
