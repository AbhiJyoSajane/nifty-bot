import requests
import time
import pandas as pd

API_KEY = "LC3NyEhz3Lchc5hqlNZ4HFK8glC4nH"
API_SECRET = "BMb2VomcS7gess3jeJcUHgbddT3ZcnvwqfkIOwIKZ9gAggfVwcIlIcfjNuEM"

BASE_URL = "https://api.delta.exchange"

SYMBOL = "BTCUSDT"
QTY = 1

def get_price():
    url = f"{BASE_URL}/v2/tickers/{SYMBOL}"
    res = requests.get(url).json()
    return float(res['result']['last_price'])

def get_candles():
    url = f"{BASE_URL}/v2/history/candles"
    params = {
        "symbol": SYMBOL,
        "resolution": "5",
        "limit": 100
    }
    res = requests.get(url, params=params).json()
    df = pd.DataFrame(res['result'])
    df['close'] = df['close'].astype(float)
    return df

def calculate_indicators(df):
    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()

    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    return df

position = None
entry_price = 0

while True:
    try:
        df = get_candles()
        df = calculate_indicators(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        price = last['close']

        # BUY CONDITION
        if (prev['ema9'] < prev['ema21'] and last['ema9'] > last['ema21'] and last['rsi'] > 50 and position is None):
            print("BUY SIGNAL")
            position = "BUY"
            entry_price = price

        # SELL CONDITION
        elif (prev['ema9'] > prev['ema21'] and last['ema9'] < last['ema21'] and last['rsi'] < 50 and position == "BUY"):
            print("SELL SIGNAL")
            position = None

        # STOP LOSS / TARGET
        if position == "BUY":
            if price <= entry_price * (1 - 0.015):
                print("STOP LOSS HIT")
                position = None

            elif price >= entry_price * (1 + 0.03):
                print("TARGET HIT")
                position = None

        time.sleep(60)

    except Exception as e:
        print("Error:", e)
        time.sleep(60)
