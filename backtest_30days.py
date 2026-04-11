import os
import pandas as pd
from kiteconnect import KiteConnect
from datetime import datetime, timedelta

# =========================
# LOAD ENV VARIABLES
# =========================
API_KEY = os.environ.get("API_KEY")
API_SECRET = os.environ.get("API_SECRET")
REQUEST_TOKEN = os.environ.get("REQUEST_TOKEN")

# =========================
# CONNECT KITE
# =========================
kite = KiteConnect(api_key=API_KEY)

try:
    session = kite.generate_session(REQUEST_TOKEN, api_secret=API_SECRET)
    ACCESS_TOKEN = session["access_token"]
    kite.set_access_token(ACCESS_TOKEN)
    print("✅ Access Token Generated Successfully")
except Exception as e:
    print("❌ Error generating access token:", e)
    exit()


# =========================
# FETCH NIFTY DATA
# =========================
def get_nifty_data():
    print("📊 Fetching Nifty Data...")

    instrument_token = 256265  # NIFTY 50
    to_date = datetime.now()
    from_date = to_date - timedelta(days=30)

    data = kite.historical_data(
        instrument_token,
        from_date,
        to_date,
        "5minute"
    )

    df = pd.DataFrame(data)

    if df.empty:
        print("❌ No data received")
        exit()

    return df


# =========================
# STRATEGY LOGIC
# =========================
def inside_candle_backtest(df):
    capital = 20000
    risk_per_trade = 200
    trades = []

    print("🚀 Running Strategy...")

    for i in range(2, len(df)):
        prev = df.iloc[i-1]
        prev2 = df.iloc[i-2]
        curr = df.iloc[i]

        # Inside Candle
        inside = prev['high'] < prev2['high'] and prev['low'] > prev2['low']

        if not inside:
            continue

        mother_high = prev2['high']
        mother_low = prev2['low']

        # ===== BUY =====
        if curr['close'] > mother_high:
            entry = curr['close']
            sl = mother_low
            risk = entry - sl

            if risk <= 0:
                continue

            target = entry + (risk * 2)
            result = 0

            for j in range(i+1, len(df)):
                high = df.iloc[j]['high']
                low = df.iloc[j]['low']

                if low <= sl:
                    result = -risk_per_trade
                    break

                if high >= target:
                    result = risk_per_trade * 2
                    break

            capital += result

            trades.append({
                "type": "BUY",
                "entry": entry,
                "exit_pnl": result,
                "capital": capital
            })

        # ===== SELL =====
        elif curr['close'] < mother_low:
            entry = curr['close']
            sl = mother_high
            risk = sl - entry

            if risk <= 0:
                continue

            target = entry - (risk * 2)
            result = 0

            for j in range(i+1, len(df)):
                high = df.iloc[j]['high']
                low = df.iloc[j]['low']

                if high >= sl:
                    result = -risk_per_trade
                    break

                if low <= target:
                    result = risk_per_trade * 2
                    break

            capital += result

            trades.append({
                "type": "SELL",
                "entry": entry,
                "exit_pnl": result,
                "capital": capital
            })

    return trades, capital


# =========================
# MAIN EXECUTION
# =========================
if __name__ == "__main__":
    df = get_nifty_data()

    trades, final_capital = inside_candle_backtest(df)

    print("\n📊 ===== BACKTEST RESULT =====")
    print(f"Total Trades: {len(trades)}")
    print(f"Final Capital: ₹{final_capital}")

    if trades:
        print("\nLast 5 Trades:")
        for t in trades[-5:]:
            print(t)
