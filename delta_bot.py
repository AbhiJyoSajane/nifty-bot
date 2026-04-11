import requests
import time
import pandas as pd
import numpy as np

BASE_URL = "https://api.delta.exchange"
SYMBOL = "BTCUSDT"

capital = 100
position = None
entry_price = 0
position_size = 0
trades = []


def get_candles():
    end = int(time.time())
    start = end - (60 * 60 * 24 * 5)

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
    df[['open','high','low','close']] = df[['open','high','low','close']].astype(float)

    return df


def supertrend(df, period=10, multiplier=3):
    hl2 = (df['high'] + df['low']) / 2

    df['tr'] = np.maximum(df['high'] - df['low'],
                         np.maximum(abs(df['high'] - df['close'].shift()),
                                    abs(df['low'] - df['close'].shift())))

    df['atr'] = df['tr'].rolling(period).mean()

    df['upperband'] = hl2 + (multiplier * df['atr'])
    df['lowerband'] = hl2 - (multiplier * df['atr'])

    df['trend'] = True

    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['upperband'].iloc[i-1]:
            df.loc[i, 'trend'] = True
        elif df['close'].iloc[i] < df['lowerband'].iloc[i-1]:
            df.loc[i, 'trend'] = False
        else:
            df.loc[i, 'trend'] = df['trend'].iloc[i-1]

    return df


def run_backtest():
    global capital, position, entry_price, position_size

    df = get_candles()

    if df.empty:
        print("No data fetched")
        return

    df = supertrend(df)

    wins = 0
    losses = 0

    for i in range(20, len(df)):
        row = df.iloc[i]
        price = row['close']

        # BUY
        if row['trend'] == True and position is None:
            position = "BUY"
            entry_price = price
            position_size = capital * 0.1  # 10% capital

        # SELL
        elif row['trend'] == False and position == "BUY":
            pnl = (price - entry_price) / entry_price * position_size
            capital += pnl
            trades.append(pnl)

            if pnl > 0:
                wins += 1
            else:
                losses += 1

            position = None

    print("\n===== SUPER TREND RESULT =====")
    print("Total Trades:", len(trades))
    print("Wins:", wins)
    print("Losses:", losses)

    if len(trades) > 0:
        print("Win Rate:", (wins / len(trades)) * 100)

    print("Final Capital:", round(capital, 2))
    print("Total Profit:", round(capital - 100, 2))


run_backtest()
