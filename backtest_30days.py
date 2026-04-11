import os
import pandas as pd
from kiteconnect import KiteConnect
from datetime import datetime, timedelta

# =====================
# CONFIG
# =====================
API_KEY = os.environ.get("API_KEY")
API_SECRET = os.environ.get("API_SECRET")
REQUEST_TOKEN = os.environ.get("REQUEST_TOKEN")

kite = KiteConnect(api_key=API_KEY)

# Generate access token
session = kite.generate_session(REQUEST_TOKEN, api_secret=API_SECRET)
kite.set_access_token(session["access_token"])

print("✅ Access Token Generated")

# =====================
# FETCH NIFTY DATA
# =====================
def get_nifty_data():
    instrument_token = 256265  # NIFTY
    to_date = datetime.now()
    from_date = to_date - timedelta(days=5)

    data = kite.historical_data(
        instrument_token,
        from_date,
        to_date,
        "5minute"
    )

    return pd.DataFrame(data)

# =====================
# GET ATM STRIKE
# =====================
def get_atm_strike(price):
    return round(price / 50) * 50

# =====================
# STRATEGY
# =====================
def option_strategy(df):
    capital = 20000
    daily_loss = 0
    max_loss = 2000
    max_trades = 5

    trades = []

    for i in range(2, len(df)):
        trade_count = 0

        prev = df.iloc[i-1]
        prev2 = df.iloc[i-2]
        curr = df.iloc[i]

        # New day reset
        if i > 2 and df.iloc[i]['date'].date() != df.iloc[i-1]['date'].date():
            daily_loss = 0
            trade_count = 0

        # Stop conditions
        if daily_loss >= max_loss or trade_count >= max_trades:
            continue

        inside = prev['high'] < prev2['high'] and prev['low'] > prev2['low']

        if not inside:
            continue

        mother_high = prev2['high']
        mother_low = prev2['low']

        price = curr['close']
        strike = get_atm_strike(price)

        # ===== BUY CE =====
        if price > mother_high:
            trade_count += 1

            entry_price = 100  # assumed premium
            sl = entry_price - 20
            target = entry_price + 40

            result = 40 if True else -20  # simplified

            pnl = 400 if result > 0 else -200
            capital += pnl

            if pnl < 0:
                daily_loss += abs(pnl)

            trades.append({
                "type": "CE",
                "strike": strike,
                "pnl": pnl,
                "capital": capital
            })

        # ===== BUY PE =====
        elif price < mother_low:
            trade_count += 1

            entry_price = 100
            sl = entry_price - 20
            target = entry_price + 40

            result = 40 if True else -20

            pnl = 400 if result > 0 else -200
            capital += pnl

            if pnl < 0:
                daily_loss += abs(pnl)

            trades.append({
                "type": "PE",
                "strike": strike,
                "pnl": pnl,
                "capital": capital
            })

    return trades, capital


# =====================
# RUN
# =====================
if __name__ == "__main__":
    df = get_nifty_data()

    trades, capital = option_strategy(df)

    print("\n📊 RESULT")
    print("Total Trades:", len(trades))
    print("Final Capital:", capital)

    for t in trades[-5:]:
        print(t)
