import pandas as pd

def inside_candle_strategy(df):
    trades = []

    for i in range(2, len(df)):
        prev = df.iloc[i-1]
        prev2 = df.iloc[i-2]
        curr = df.iloc[i]

        # Inside candle condition
        inside = prev['high'] < prev2['high'] and prev['low'] > prev2['low']

        if inside:
            mother_high = prev2['high']
            mother_low = prev2['low']

            # BUY breakout
            if curr['close'] > mother_high:
                entry = curr['close']
                sl = mother_low
                target = entry + (entry - sl) * 2

                trades.append({
                    "type": "BUY",
                    "entry": entry,
                    "sl": sl,
                    "target": target
                })

            # SELL breakout
            elif curr['close'] < mother_low:
                entry = curr['close']
                sl = mother_high
                target = entry - (sl - entry) * 2

                trades.append({
                    "type": "SELL",
                    "entry": entry,
                    "sl": sl,
                    "target": target
                })

    return trades
