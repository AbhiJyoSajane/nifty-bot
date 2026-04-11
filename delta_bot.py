import requests
import time
import pandas as pd

BASE_URL = "https://api.delta.exchange"

SYMBOL = "BTCUSDT"

MODE = "BACKTEST"   # keep BACKTEST for now

position = None
entry_price = 0
trades = []
balance = 1000


def get_candles():
    end = int(time.time())
    start = end - (60 * 60 * 24 * 5)  # last 5 days

    url = f"{BASE_URL}/v2/history/candles"

    params = {
        "symbol": SYMBOL,
        "resolution": "5m",
        "start": start,
        "end": end
    }

    res = requests.get(url, params=params).json()

    if 'result' not in res:
        print("API Error:", res)
        return pd.DataFrame()

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


def run_backtest():
    global position, entry_price, balance

    df = get_candles()
    df = calculate_indicators(df)

    wins = 0
    losses = 0

    for i in range(30, len(df)):
        row = df.iloc[i]
        price = row['close']

        # ✅ BUY (UPDATED STRATEGY)
        if (row['ema9'] > row['ema21'] and row['rsi'] > 55 and row['close'] > row['ema21'] and position is None):
            position = "BUY"
            entry_price = price

        # ✅ SELL (UPDATED STRATEGY)
        elif (row['ema9'] < row['ema21'] and row['rsi'] < 45 and position == "BUY"):
            pnl = price - entry_price
            trades.append(pnl)
            balance += pnl

            if pnl > 0:
                wins += 1
            else:
                losses += 1

            position = None

        # ✅ SL / TARGET (UPDATED)
        if position == "BUY":
            # Stop Loss 1.2%
            if price <= entry_price * (1 - 0.012):
                pnl = price - entry_price
                trades.append(pnl)
                balance += pnl
                losses += 1
                position = None

            # Target 2%
            elif price >= entry_price * (1 + 0.02):
                pnl = price - entry_price
                trades.append(pnl)
                balance += pnl
                wins += 1
                position = None

    # RESULTS
    print("\n===== BACKTEST RESULT =====")
    print("Total Trades:", len(trades))
    print("Wins:", wins)
    print("Losses:", losses)

    if len(trades) > 0:
        print("Win Rate:", (wins / len(trades)) * 100)

    print("Final Balance:", balance)
    print("Total P/L:", sum(trades))


# ===== RUN =====
if MODE == "BACKTEST":
    run_backtest()
