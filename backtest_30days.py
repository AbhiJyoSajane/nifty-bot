import pandas as pd

def inside_candle_backtest():
    print("Bot running successfully ✅")

    data = {
        "high": [10, 11, 12, 11, 10, 9],
        "low": [8, 9, 10, 9, 8, 7],
        "close": [9, 10, 11, 10, 9, 8]
    }

    df = pd.DataFrame(data)

    trades = []
    capital = 20000

    for i in range(2, len(df)):
        prev = df.iloc[i-1]
        prev2 = df.iloc[i-2]
        curr = df.iloc[i]

        inside = prev['high'] < prev2['high'] and prev['low'] > prev2['low']

        if inside:
            if curr['close'] > prev2['high']:
                trades.append("BUY")
                capital += 400

            elif curr['close'] < prev2['low']:
                trades.append("SELL")
                capital += 400

    print("Trades:", trades)
    print("Final Capital:", capital)


if __name__ == "__main__":
    inside_candle_backtest()
