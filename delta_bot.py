import requests
import time
import pandas as pd

BASE_URL = "https://api.delta.exchange"
SYMBOL = "BTCUSDT"
QTY = 1

position = None
entry_price = 0


def get_candles():
    try:
        end = int(time.time())
        start = end - (60 * 60 * 5)  # last 5 hours

        url = f"{BASE_URL}/v2/history/candles"
        params = {
            "symbol": SYMBOL,
            "resolution": "5m",
            "start": start,
            "end": end
        }

        res = requests.get(url, params=params).json()

        if 'result' not in res:
            print("Candle API Error:", res)
            return pd.DataFrame()

        df = pd.DataFrame(res['result'])

        if df.empty:
            return df

        df['close'] = df['close'].astype(float)
        return df

    except Exception as e:
        print("Candle Error:", e)
        return pd.DataFrame()


def calculate_indicators(df):
    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()

    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    return df


def print_status(price, rsi, pos, entry):
    if pos:
        pl = ((price - entry) / entry) * 100
        print(f"[ACTIVE POSITION] {pos} | Entry: {entry:.2f} | Current: {price:.2f} | P/L: {pl:.2f}% | RSI: {rsi:.2f}")
    else:
        print(f"[NO POSITION] Price: {price:.2f} | RSI: {rsi:.2f}")


while True:
    try:
        df = get_candles()

        if df.empty or len(df) < 30:
            print("Waiting for data...")
            time.sleep(60)
            continue

        df = calculate_indicators(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        price = last['close']
        rsi = last['rsi']

        print_status(price, rsi, position, entry_price)

        # BUY CONDITION
        if (prev['ema9'] < prev['ema21'] and last['ema9'] > last['ema21'] and last['rsi'] > 50 and position is None):
            print(f"✅ BUY SIGNAL at {price:.2f} | RSI: {rsi:.2f}")
            position = "BUY"
            entry_price = price

        # SELL CONDITION (exit)
        elif (prev['ema9'] > prev['ema21'] and last['ema9'] < last['ema21'] and last['rsi'] < 50 and position == "BUY"):
            print(f"🔻 SELL SIGNAL (Opposite) at {price:.2f} | RSI: {rsi:.2f}")
            position = None

        # SL / TARGET
        if position == "BUY":
            if price <= entry_price * (1 - 0.015):
                print(f"⛔ STOP LOSS HIT at {price:.2f}")
                position = None
            elif price >= entry_price * (1 + 0.03):
                print(f"🏁 TARGET HIT at {price:.2f}")
                position = None

        time.sleep(60)

    except Exception as e:
        print("MAIN ERROR:", e)
        time.sleep(60)
