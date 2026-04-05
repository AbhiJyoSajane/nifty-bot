def apply_strategy(df):

    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()

    df['date'] = df.index.date

    # Yesterday High/Low
    daily = df.resample('1D').agg({'high':'max','low':'min'})
    daily['prev_high'] = daily['high'].shift(1)
    daily['prev_low'] = daily['low'].shift(1)

    # Weekly High/Low
    weekly = df.resample('1W').agg({'high':'max','low':'min'})
    weekly['week_high'] = weekly['high'].shift(1)
    weekly['week_low'] = weekly['low'].shift(1)

    trades = []

    grouped = df.groupby('date')

    for date, day in grouped:

        day = day.copy()

        if len(day) < 5:
            continue

        daily_pnl = 0
        trades_today = 0

        # ORB
        orb_high = day.iloc[:3]['high'].max()
        orb_low = day.iloc[:3]['low'].min()

        # Get filters
        try:
            y_high = daily.loc[str(date)]['prev_high']
            y_low = daily.loc[str(date)]['prev_low']
            w_high = weekly.loc[:str(date)].iloc[-1]['week_high']
            w_low = weekly.loc[:str(date)].iloc[-1]['week_low']
        except:
            continue

        position = None
        entry = sl = target = 0

        for i in range(3, len(day)):

            row = day.iloc[i]

            if trades_today >= MAX_TRADES:
                break

            if daily_pnl <= MAX_DAILY_LOSS:
                break

            # ENTRY
            if position is None:

                # STRONG BUY
                if (row['close'] > orb_high and
                    row['ema9'] > row['ema21'] and
                    row['close'] > y_high and
                    row['close'] > w_high):

                    position = 'LONG'
                    entry = row['close']
                    sl = orb_low
                    target = entry + (entry - sl) * 2
                    trades_today += 1

                # STRONG SELL
                elif (row['close'] < orb_low and
                      row['ema9'] < row['ema21'] and
                      row['close'] < y_low and
                      row['close'] < w_low):

                    position = 'SHORT'
                    entry = row['close']
                    sl = orb_high
                    target = entry - (sl - entry) * 2
                    trades_today += 1

            # EXIT
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
