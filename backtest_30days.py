import pandas as pd

def load_data():
    # Replace with your data source (CSV or API)
    df = pd.read_csv("data.csv")  
    df.columns = [c.lower() for c in df.columns]
    return df


def inside_candle_backtest(df):
    capital = 20000
    risk_per_trade = 200  # fixed risk
    trades = []

    for i in range(2, len(df)):
        prev = df.iloc[i-1]
        prev2 = df.iloc[i-2]
        curr = df.iloc[i]

        # Inside Candle
        inside = prev['high'] < prev2['high'] and prev['low'] > prev2['low']

        if not inside:
            continue

        mother_high = prev2['high']
        mother_low = prev2['low']

        # ===== BUY =====
        if curr['close'] > mother_high:
            entry = curr['close']
            sl = mother_low
            risk = entry - sl

            if risk <= 0:
                continue

            qty = risk_per_trade / risk
            target = entry + (risk * 2)

            result = 0

            # simulate forward candles
            for j in range(i+1, len(df)):
                high = df.iloc[j]['high']
                low = df.iloc[j]['low']

                if low <= sl:
                    result = -risk_per_trade
                    break

                if high >= target:
                    result = risk_per_trade * 2
                    break

            capital += result

            trades.append({
                "type": "BUY",
                "entry": entry,
                "sl": sl,
                "target": target,
                "pnl": result,
                "capital": capital
            })

        # ===== SELL =====
        elif curr['close'] < mother_low:
            entry = curr['close']
            sl = mother_high
            risk = sl - entry

            if risk <= 0:
                continue

            qty = risk_per_trade / risk
            target = entry - (risk * 2)

            result = 0

            for j in range(i+1, len(df)):
                high = df.iloc[j]['high']
                low = df.iloc[j]['low']

                if high >= sl:
                    result = -risk_per_trade
                    break

                if low <= target:
                    result = risk_per_trade * 2
                    break

            capital += result

            trades.append({
                "type": "SELL",
                "entry": entry,
                "sl": sl,
                "target": target,
                "pnl": result,
                "capital": capital
            })

    return trades, capital


if __name__ == "__main__":
    df = load_data()
    trades, final_capital = inside_candle_backtest(df)

    print(f"Total Trades: {len(trades)}")
    print(f"Final Capital: ₹{final_capital}")

    for t in trades[-5:]:
        print(t)
