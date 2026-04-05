def apply_strategy(df):

    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()

    df['date'] = df.index.date

    trades = []

    grouped = df.groupby('date')

    for date, day in grouped:

        day = day.copy()

        if len(day) < 5:
            continue

        daily_pnl = 0
        trades_today = 0

        # ORB levels
        orb_high = day.iloc[:3]['high'].max()
        orb_low = day.iloc[:3]['low'].min()

        position = None
        entry = 0
        sl = 0
        target = 0

        for i in range(3, len(day)):

            row = day.iloc[i]

            if trades_today >= 5:
                break

            if daily_pnl <= -2000:
                break

            # ENTRY
            if position is None:

                # LONG
                if row['close'] > orb_high and row['ema9'] > row['ema21']:
                    position = 'LONG'
                    entry = row['close']
                    sl = orb_low
                    target = entry + (entry - sl) * 2
                    trades_today += 1

                # SHORT
                elif row['close'] < orb_low and row['ema9'] < row['ema21']:
                    position = 'SHORT'
                    entry = row['close']
                    sl = orb_high
                    target = entry - (sl - entry) * 2
                    trades_today += 1

            # EXIT LOGIC
            elif position == 'LONG':

                if row['low'] <= sl:
                    pnl = (sl - entry) * LOT_SIZE
                    trades.append(pnl)
                    daily_pnl += pnl
                    position = None

                elif row['high'] >= target:
                    pnl = (target - entry) * LOT_SIZE
                    trades.append(pnl)
                    daily_pnl += pnl
                    position = None

            elif position == 'SHORT':

                if row['high'] >= sl:
                    pnl = (entry - sl) * LOT_SIZE
                    trades.append(pnl)
                    daily_pnl += pnl
                    position = None

                elif row['low'] <= target:
                    pnl = (entry - target) * LOT_SIZE
                    trades.append(pnl)
                    daily_pnl += pnl
                    position = None

    return trades
