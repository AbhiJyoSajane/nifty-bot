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
    all_data = []

    for i in range(12):  # more loops for 3m data
        start = end - (60 * 60 * 6)  # 6 hours chunk

        url = f"{BASE_URL}/v2/history/candles"
        params = {
            "symbol": SYMBOL,
            "resolution": "3m",
            "start": start,
            "end": end
        }

        res = requests.get(url, params=params).json()

        if 'result' not in res:
            print("API Error:", res)
            break

        data = res['result']
        all_data.extend(data)

        end = start  # move backward

    df = pd.DataFrame(all_data)

    if df.empty:
        print("No data fetched")
        return df

    df[['open','high','low','close']] = df[['open','high','low','close']].astype(float)

    # sort + remove duplicates
    df = df.sort_values(by='time').drop_duplicates().reset_index(drop=True)

    print("Total candles:", len(df))
    return df


def calculate_ema(df):
    df['ema200'] = df['close'].ewm(span=200).mean()
    return df


def supertrend(df, period=10, multiplier=3):
    df['hl2'] = (df['high'] + df['low']) / 2

    df['tr'] = np.maximum(df['high'] - df['low'],
                         np.maximum(abs(df['high'] - df['close'].shift()),
                                    abs(df['low'] - df['close'].shift())))

    df['atr'] = df['tr'].rolling(period).mean()

    df['upperband'] = df['hl2'] + multiplier * df['atr']
    df['lowerband'] = df['hl2'] - multiplier * df['atr']

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

    if len(df) < 200:
        print("Not enough data")
        return

    df = calculate_ema(df)
    df = supertrend(df)

    wins = 0
    losses = 0

    for i in range(200, len(df)):
        row = df.iloc[i]
        price = row['close']

        # BUY
        if row['trend'] and price > row['ema200'] and position is None:
            position = "BUY"
            entry_price = price
            position_size = capital * 0.1

        # SELL
        elif not row['trend'] and position == "BUY":
            pnl = (price - entry_price) / entry_price * position_size
            capital += pnl
            trades.append(pnl)

            if pnl > 0:
                wins += 1
            else:
                losses += 1

            position = None

    print("\n===== FINAL 3M RESULT =====")
    print("Total Trades:", len(trades))
    print("Wins:", wins)
    print("Losses:", losses)

    if len(trades) > 0:
        print("Win Rate:", (wins / len(trades)) * 100)

    print("Final Capital:", round(capital, 2))
    print("Profit:", round(capital - 100, 2))


run_backtest()
