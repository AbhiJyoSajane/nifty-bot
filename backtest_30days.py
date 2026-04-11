import os
import pandas as pd
from kiteconnect import KiteConnect
from datetime import datetime, timedelta

# =====================
# CONFIG
# =====================
API_KEY = os.environ.get("API_KEY")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

print("✅ Connected")

# =====================
# LOAD INSTRUMENTS
# =====================
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
    capital = 20000
    max_daily_loss = 2000
    max_trades = 5

    trades = []

    current_day = None
    daily_loss = 0
    trade_count = 0

    for i in range(2, len(df)):
        row_date = df.iloc[i]['date'].date()

        # Reset per day
        if current_day != row_date:
            current_day = row_date
            daily_loss = 0
            trade_count = 0

        if daily_loss >= max_daily_loss or trade_count >= max_trades:
            continue

        prev = df.iloc[i-1]
        prev2 = df.iloc[i-2]
        curr = df.iloc[i]

        # Inside Candle
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
            sl_nifty = mother_low
            entry_nifty = price

        elif price < mother_low:
            direction = "PE"
            sl_nifty = mother_high
            entry_nifty = price

        else:
            continue

        # Risk in NIFTY
        risk_nifty = abs(entry_nifty - sl_nifty)

        if risk_nifty == 0:
            continue

        token = get_option_token(strike, direction)
        if token is None:
            continue

        from_date = curr['date'].to_pydatetime()
        option_df = get_option_data(token, from_date)

        if option_df.empty:
            continue

        entry_option = option_df.iloc[0]['close']

        # Convert risk into option move (approx ratio)
        sl_option = entry_option * 0.8
        target_option = entry_option * 1.4

        # Position sizing based on ₹2000 risk
        risk_per_lot = entry_option - sl_option
        if risk_per_lot <= 0:
            continue

        qty = int(max_daily_loss / risk_per_lot)

        result = 0

        for j in range(1, len(option_df)):
            high = option_df.iloc[j]['high']
            low = option_df.iloc[j]['low']

            if low <= sl_option:
                result = -risk_per_lot * qty
                break

            if high >= target_option:
                result = (target_option - entry_option) * qty
                break

        capital += result
        trade_count += 1

        if result < 0:
            daily_loss += abs(result)

        trades.append({
            "date": str(row_date),
            "type": direction,
            "strike": strike,
            "entry": float(entry_option),
            "qty": qty,
            "pnl": round(result, 2),
            "capital": round(capital, 2)
        })

    return trades, capital

# =====================
# RUN
# =====================
if __name__ == "__main__":
    df = get_nifty_data()

    trades, capital = run_strategy(df)

    print("\n📊 FINAL RESULT")
    print("Total Trades:", len(trades))
    print("Final Capital:", round(capital, 2))

    for t in trades[-5:]:
        print(t)
