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

LOT_SIZE = 65
START_CAPITAL = 20000
MAX_DAILY_LOSS = 2000
MAX_TRADES_PER_DAY = 5

SL_POINTS = 20
TARGET_POINTS = 40

kite = KiteConnect(api_key=API_KEY)

# =====================
# TOKEN
# =====================
try:
    session = kite.generate_session(REQUEST_TOKEN, api_secret=API_SECRET)
    kite.set_access_token(session["access_token"])
    print("✅ Access Token Generated")
except Exception as e:
    print("❌ Token Error:", e)
    exit()

# =====================
# VERIFY
# =====================
try:
    print("👤", kite.profile()["user_name"])
except:
    print("❌ Login Failed")
    exit()

# =====================
# LOAD INSTRUMENTS
# =====================
print("📦 Loading instruments...")
instruments = kite.instruments("NFO")

def get_option_token(strike, option_type):
    for ins in instruments:
        if (
            ins["name"] == "NIFTY" and
            ins["strike"] == strike and
            ins["instrument_type"] == option_type and
            ins["expiry"] >= datetime.now().date()
        ):
            return ins["instrument_token"]
    return None

# =====================
# FETCH NIFTY
# =====================
def get_nifty_data():
    data = kite.historical_data(
        256265,
        datetime.now() - timedelta(days=5),
        datetime.now(),
        "5minute"
    )
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df

# =====================
# ATM STRIKE
# =====================
def get_atm(price):
    return round(price / 50) * 50

# =====================
# OPTION DATA
# =====================
def get_option_data(token, from_date):
    to_date = from_date + timedelta(days=1)

    data = kite.historical_data(token, from_date, to_date, "5minute")
    df = pd.DataFrame(data)

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])

    return df

# =====================
# STRATEGY
# =====================
def run_strategy(df):
    capital = START_CAPITAL

    current_day = None
    daily_loss = 0
    trade_count = 0

    trades = []

    for i in range(2, len(df)):
        row_date = df.iloc[i]['date'].date()

        # Reset day
        if current_day != row_date:
            current_day = row_date
            daily_loss = 0
            trade_count = 0

        if daily_loss >= MAX_DAILY_LOSS or trade_count >= MAX_TRADES_PER_DAY:
            continue

        prev = df.iloc[i-1]
        prev2 = df.iloc[i-2]
        curr = df.iloc[i]

        inside = prev['high'] < prev2['high'] and prev['low'] > prev2['low']
        if not inside:
            continue

        mother_high = prev2['high']
        mother_low = prev2['low']

        price = curr['close']
        strike = get_atm(price)

        direction = None
        if price > mother_high:
            direction = "CE"
        elif price < mother_low:
            direction = "PE"
        else:
            continue

        token = get_option_token(strike, direction)
        if token is None:
            continue

        from_date = curr['date'].to_pydatetime()
        option_df = get_option_data(token, from_date)

        if option_df.empty:
            continue

        entry = option_df.iloc[0]['close']

        # ✅ PREMIUM BASED SL/TARGET
        sl = entry - SL_POINTS
        target = entry + TARGET_POINTS

        if sl <= 0:
            continue

        # CAPITAL CHECK
        cost = entry * LOT_SIZE
        if cost > capital:
            continue

        result = 0

        for j in range(1, len(option_df)):
            high = option_df.iloc[j]['high']
            low = option_df.iloc[j]['low']

            if low <= sl:
                result = -SL_POINTS * LOT_SIZE
                break

            if high >= target:
                result = TARGET_POINTS * LOT_SIZE
                break

        capital += result
        trade_count += 1

        if result < 0:
            daily_loss += abs(result)

        trades.append({
            "date": str(row_date),
            "type": direction,
            "strike": strike,
            "entry": float(entry),
            "lot": 1,
            "pnl": result,
            "capital": capital
        })

    return trades, capital

# =====================
# RUN
# =====================
if __name__ == "__main__":
    print("📊 Fetching Nifty...")
    df = get_nifty_data()

    print("🚀 Running Strategy...")
    trades, capital = run_strategy(df)

    print("\n📊 FINAL RESULT")
    print("Total Trades:", len(trades))
    print("Final Capital:", capital)

    for t in trades[-5:]:
        print(t)
