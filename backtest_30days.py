from kiteconnect import KiteConnect
import pandas as pd
import datetime as dt
import time

# ---------------- CONFIG ---------------- #
API_KEY = "your_api_key"
ACCESS_TOKEN = "your_access_token"

CAPITAL = 20000
MAX_DAILY_LOSS = -2000
LOT_SIZE = 50
RISK_PER_TRADE = 500   # optional safety

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# ---------------- GLOBAL ---------------- #
daily_pnl = 0
position = None


# ---------------- GET NIFTY DATA ---------------- #
def get_nifty_data():
    instrument_token = 256265
    data = kite.historical_data(
        instrument_token,
        dt.datetime.now().replace(hour=9, minute=15),
        dt.datetime.now(),
        "5minute"
    )
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df


# ---------------- ATM STRIKE ---------------- #
def get_atm_strike(price):
    return round(price / 50) * 50


# ---------------- AUTO EXPIRY (SIMPLE) ---------------- #
def get_expiry():
    today = dt.date.today()
    next_thursday = today + dt.timedelta((3 - today.weekday()) % 7)
    return next_thursday.strftime("%d%b").upper()


# ---------------- OPTION SYMBOL ---------------- #
def get_option_symbol(strike, option_type):
    expiry = get_expiry()
    return f"NFO:NIFTY{expiry}{strike}{option_type}"


# ---------------- GET LTP ---------------- #
def get_ltp(symbol):
    return kite.ltp(symbol)[symbol]['last_price']


# ---------------- ORDER ---------------- #
def place_order(symbol):
    return kite.place_order(
        variety=kite.VARIETY_REGULAR,
        exchange=kite.EXCHANGE_NFO,
        tradingsymbol=symbol.split(":")[1],
        transaction_type=kite.TRANSACTION_TYPE_BUY,
        quantity=LOT_SIZE,
        product=kite.PRODUCT_MIS,
        order_type=kite.ORDER_TYPE_MARKET
    )


# ---------------- STRATEGY ---------------- #
def run_strategy():
    global position, daily_pnl

    df = get_nifty_data()

    # ORB RANGE
    orb = df[(df['date'].dt.time >= dt.time(9, 15)) &
             (df['date'].dt.time <= dt.time(9, 45))]

    if len(orb) < 6:
        return

    orb_high = orb['high'].max()
    orb_low = orb['low'].min()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    price = last['close']

    # VOLUME CONFIRMATION
    vol_avg = df['volume'].rolling(20).mean().iloc[-1]
    vol_ok = last['volume'] > vol_avg

    # CANDLE CONFIRMATION
    bullish = last['close'] > last['open']
    bearish = last['close'] < last['open']

    # ---------------- ENTRY ---------------- #
    if position is None:

        # BUY CE
        if price > orb_high and bullish and vol_ok:

            strike = get_atm_strike(price)
            symbol = get_option_symbol(strike, "CE")

            premium = get_ltp(symbol)

            print("BUY CE:", symbol, premium)
            place_order(symbol)

            position = {
                "symbol": symbol,
                "type": "CE",
                "entry": premium,
                "sl": premium - 10,
                "target": premium + 20,
                "trail": premium - 10
            }

        # BUY PE
        elif price < orb_low and bearish and vol_ok:

            strike = get_atm_strike(price)
            symbol = get_option_symbol(strike, "PE")

            premium = get_ltp(symbol)

            print("BUY PE:", symbol, premium)
            place_order(symbol)

            position = {
                "symbol": symbol,
                "type": "PE",
                "entry": premium,
                "sl": premium - 10,
                "target": premium + 20,
                "trail": premium - 10
            }

    # ---------------- EXIT ---------------- #
    if position:

        ltp = get_ltp(position["symbol"])

        # TRAILING LOGIC
        if ltp > position["entry"] + 10:
            position["trail"] = max(position["trail"], ltp - 10)

        exit_price = None

        if ltp <= position["trail"]:
            exit_price = ltp
            print("TRAIL HIT")

        elif ltp >= position["target"]:
            exit_price = ltp
            print("TARGET HIT")

        if exit_price:
            pnl = (exit_price - position["entry"]) * LOT_SIZE
            daily_pnl += pnl

            print(f"EXIT {position['symbol']} | PnL: {pnl} | Daily: {daily_pnl}")

            position = None

    # ---------------- RISK CONTROL ---------------- #
    if daily_pnl <= MAX_DAILY_LOSS:
        print("MAX LOSS HIT – STOP")
        exit()


# ---------------- LOOP ---------------- #
while True:
    try:
        now = dt.datetime.now().time()

        if dt.time(9, 46) <= now <= dt.time(15, 15):
            run_strategy()

        time.sleep(30)

    except Exception as e:
        print("Error:", e)
        time.sleep(30)
