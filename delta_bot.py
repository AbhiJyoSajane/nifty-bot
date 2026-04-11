import requests
import time
import pandas as pd

BASE_URL = "https://api.delta.exchange"

SYMBOL = "BTCUSDT"
QTY = 1

MODE = "BACKTEST"   # change to LIVE later

position = None
entry_price = 0
trades = []
balance = 1000  # starting capital


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

        # BUY
        if (row['ema9'] > row['ema21'] and row['rsi'] > 50 and position is None):
            position = "BUY"
            entry_price = price

        # SELL (opposite)
        elif (row['ema9'] < row['ema21'] and row['rsi'] < 50 and position == "BUY"):
            pnl = price - entry_price
            trades.append(pnl)
            balance += pnl

            if pnl > 0:
                wins += 1
            else:
                losses += 1

            position = None

        # SL / TARGET
        if position == "BUY":
            if price <= entry_price * (1 - 0.015):
                pnl = price - entry_price
                trades.append(pnl)
                balance += pnl
                losses += 1
                position = None

            elif price >= entry_price * (1 + 0.03):
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
    print("Win Rate:", (wins / len(trades)) * 100 if trades else 0)
    print("Final Balance:", balance)
    print("Total P/L:", sum(trades))


def run_live():
    global position, entry_price

    while True:
        try:
            df = get_candles()

            if df.empty or len(df) < 30:
                print("Waiting for data...")
                time.sleep(60)
                continue

            df = calculate_indicators(df)

            last = df.iloc[-1]
            price = last['close']

            print(f"[{position if position else 'NO POSITION'}] Price: {price:.2f} | RSI: {last['rsi']:.2f}")

            # BUY
            if (last['ema9'] > last['ema21'] and last['rsi'] > 50 and position is None):
                print("BUY SIGNAL")
                position = "BUY"
                entry_price = price

            # SELL
            elif (last['ema9'] < last['ema21'] and last['rsi'] < 50 and position == "BUY"):
                print("SELL SIGNAL")
                position = None

            # SL / TARGET
            if position == "BUY":
                if price <= entry_price * (1 - 0.015):
                    print("STOP LOSS HIT")
                    position = None

                elif price >= entry_price * (1 + 0.03):
                    print("TARGET HIT")
                    position = None

            time.sleep(60)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(60)


# ===== MAIN =====
if MODE == "BACKTEST":
    run_backtest()
else:
    run_live()
