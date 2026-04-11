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
# ATM STRIKE
# =====================
def get_atm(price):
    return round(price / 50) * 50

# =====================
# GET OPTION TOKEN
# =====================
def get_option_token(strike, option_type):
    instruments = kite.instruments("NFO")

    for ins in instruments:
        if (
            ins["name"] == "NIFTY" and
            ins["strike"] == strike and
            ins["instrument_type"] == option_type and
            ins["expiry"] > datetime.now().date()
        ):
            return ins["instrument_token"]

    return None

# =====================
# FETCH OPTION DATA
# =====================
def get_option_data(token, from_date, to_date):
    data = kite.historical_data(token, from_date, to_date, "5minute")
    return pd.DataFrame(data)

# =====================
# STRATEGY
# =====================
def run_strategy(df):
    capital = 20000
    trades = []

    for i in range(2, len(df)):
        prev = df.iloc[i-1]
        prev2 = df.iloc[i-2]
        curr = df.iloc[i]

        inside = prev['high'] < prev2['high'] and prev['low'] > prev2['low']

        if not inside:
            continue

        price = curr['close']
        strike = get_atm(price)

        direction = None

        if price > prev2['high']:
            direction = "CE"
        elif price < prev2['low']:
            direction = "PE"
        else:
            continue

        token = get_option_token(strike, direction)

        if token is None:
            continue

        option_df = get_option_data(
            token,
            curr['date'],
            curr['date'] + timedelta(days=1)
        )

        if option_df.empty:
            continue

        entry = option_df.iloc[0]['close']

        sl = entry * 0.8        # 20% SL
        target = entry * 1.4    # 40% target (1:2 RR)

        result = 0

        for j in range(1, len(option_df)):
            high = option_df.iloc[j]['high']
            low = option_df.iloc[j]['low']

            if low <= sl:
                result = -200
                break

            if high >= target:
                result = 400
                break

        capital += result

        trades.append({
            "type": direction,
            "strike": strike,
            "entry": entry,
            "pnl": result,
            "capital": capital
        })

    return trades, capital

# =====================
# RUN
# =====================
if __name__ == "__main__":
    df = get_nifty_data()

    trades, capital = run_strategy(df)

    print("\n📊 REAL OPTION BACKTEST")
    print("Total Trades:", len(trades))
    print("Final Capital:", capital)

    if trades:
        for t in trades[-5:]:
            print(t)
