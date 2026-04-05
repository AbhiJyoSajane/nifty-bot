import pandas as pd
import yfinance as yf

# ==============================
# SETTINGS
# ==============================
SYMBOL = "^NSEI"
MAX_TRADES_PER_DAY = 5
MAX_DAILY_LOSS = -2000


# ==============================
# FETCH DATA (SAFE + STABLE)
# ==============================
def get_data():
    df = yf.download(
        SYMBOL,
        interval="5m",
        period="5d",
        progress=False
    )

    if df.empty:
        raise Exception("No data fetched")

    df.reset_index(inplace=True)

    # Standardize column names
    df.columns = [col.lower() for col in df.columns]

    # Rename datetime properly
    if 'datetime' not in df.columns:
        if 'index' in df.columns:
            df.rename(columns={'index': 'datetime'}, inplace=True)
        elif 'date' in df.columns:
            df.rename(columns={'date': 'datetime'}, inplace=True)

    # FINAL SAFETY FIX (prevents all datetime errors)
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
    df = df.dropna(subset=['datetime'])

    return df


# ==============================
# STRATEGY
# ==============================
def run_strategy(df):

    # EMA
    df['ema20'] = df['close'].ewm(span=20).mean()
    df['ema50'] = df['close'].ewm(span=50).mean()

    total_trades = 0
    wins = 0
    losses = 0
    total_profit = 0

    current_day = None
    trades_today = 0
    day_pnl = 0

    position = None
    entry_price = 0

    orb_high = None
    orb_low = None

    prev_day_high = None
    prev_day_low = None

    week_high = None
    week_low = None

    for i, row in df.iterrows():

        # 🔥 FINAL SAFE datetime handling
        dt = pd.to_datetime(row['datetime'], errors='coerce')
        if pd.isna(dt):
            continue

        day = dt.date()

        # ==============================
        # NEW DAY RESET
        # ==============================
        if current_day != day:
            current_day = day
            trades_today = 0
            day_pnl = 0

            day_data = df[df['datetime'].dt.date == day]

            # ORB (first 15 min)
            first_3 = day_data.head(3)
            if not first_3.empty:
                orb_high = first_3['high'].max()
                orb_low = first_3['low'].min()

            # Yesterday levels
            prev_day_data = df[df['datetime'].dt.date < day]
            if not prev_day_data.empty:
                last_day = prev_day_data['datetime'].dt.date.max()
                prev_day_df = prev_day_data[prev_day_data['datetime'].dt.date == last_day]
                prev_day_high = prev_day_df['high'].max()
                prev_day_low = prev_day_df['low'].min()

            # Weekly levels (approx last 5 days)
            last_5_days = df[df['datetime'] < dt].tail(375)
            if not last_5_days.empty:
                week_high = last_5_days['high'].max()
                week_low = last_5_days['low'].min()

        # ==============================
        # RISK CONTROL
        # ==============================
        if trades_today >= MAX_TRADES_PER_DAY:
            continue

        if day_pnl <= MAX_DAILY_LOSS:
            continue

        price = row['close']

        # ==============================
        # ENTRY LOGIC
        # ==============================
        if position is None:

            # ORB breakout + EMA filter
            if orb_high and price > orb_high and row['ema20'] > row['ema50']:
                position = "LONG"
                entry_price = price
                trades_today += 1
                total_trades += 1

            elif orb_low and price < orb_low and row['ema20'] < row['ema50']:
                position = "SHORT"
                entry_price = price
                trades_today += 1
                total_trades += 1

            # Backup EMA crossover
            elif row['ema20'] > row['ema50']:
                position = "LONG"
                entry_price = price
                trades_today += 1
                total_trades += 1

            elif row['ema20'] < row['ema50']:
                position = "SHORT"
                entry_price = price
                trades_today += 1
                total_trades += 1

        # ==============================
        # EXIT LOGIC
        # ==============================
        else:

            pnl = 0

            if position == "LONG":
                pnl = price - entry_price
                if price < row['ema20'] or (prev_day_low and price < prev_day_low):
                    position = None

            elif position == "SHORT":
                pnl = entry_price - price
                if price > row['ema20'] or (prev_day_high and price > prev_day_high):
                    position = None

            if position is None:
                total_profit += pnl
                day_pnl += pnl

                if pnl > 0:
                    wins += 1
                else:
                    losses += 1

    # ==============================
    # RESULT
    # ==============================
    print("===== FINAL RESULT =====")
    print("Total Trades:", total_trades)
    print("Winning Trades:", wins)
    print("Losing Trades:", losses)
    print("Win Rate:", (wins / total_trades * 100) if total_trades > 0 else 0)
    print("Total Profit:", total_profit)


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    df = get_data()
    run_strategy(df)
