from kiteconnect import KiteConnect
import pandas as pd
import datetime
import os

# =========================
# CONFIG
# =========================
api_key = os.environ.get("API_KEY")
api_secret = os.environ.get("API_SECRET")
request_token = os.environ.get("REQUEST_TOKEN")

kite = KiteConnect(api_key=api_key)
data = kite.generate_session(request_token, api_secret=api_secret)
kite.set_access_token(data["access_token"])

print("✅ Connected")

NIFTY = 256265

# =========================
# GET EXPIRY
# =========================
def get_expiry():
    today = datetime.date.today()
    thursday = today + datetime.timedelta((3 - today.weekday()) % 7)
    return thursday.strftime("%d%b").upper()

EXPIRY = get_expiry()

# =========================
# SUPERTREND FUNCTION
# =========================
def supertrend(df, period=10, multiplier=3):

    df['tr'] = df[['high','close']].max(axis=1) - df[['low','close']].min(axis=1)
    df['atr'] = df['tr'].rolling(period).mean()

    hl2 = (df['high'] + df['low']) / 2
    df['upperband'] = hl2 + multiplier * df['atr']
    df['lowerband'] = hl2 - multiplier * df['atr']

    df['supertrend'] = True

    for i in range(1, len(df)):
        if df['close'][i] > df['upperband'][i-1]:
            df.loc[i, 'supertrend'] = True
        elif df['close'][i] < df['lowerband'][i-1]:
            df.loc[i, 'supertrend'] = False
        else:
            df.loc[i, 'supertrend'] = df.loc[i-1, 'supertrend']

    return df

# =========================
# FETCH DATA
# =========================
to_date = datetime.datetime.now()
from_date = to_date - datetime.timedelta(days=30)

# NIFTY DATA (5m)
data_nifty = kite.historical_data(
    instrument_token=NIFTY,
    from_date=from_date,
    to_date=to_date,
    interval="5minute"
)

df = pd.DataFrame(data_nifty)
df.columns = [col.lower() for col in df.columns]

# =========================
# INDICATORS (NIFTY)
# =========================
df['ema9'] = df['close'].ewm(span=9).mean()
df['ema21'] = df['close'].ewm(span=21).mean()
df['ema200'] = df['close'].ewm(span=200).mean()
df['adx'] = abs(df['ema9'] - df['ema21'])

# =========================
# BACKTEST
# =========================
position = None
entry_price = 0
entry_premium = 0

LOT_SIZE = 65
TARGET = 15
SL = 10

capital = 20000
TRADE_CAPITAL = 120 * LOT_SIZE

for i in range(50, len(df)):   # start later (need data)

    row = df.iloc[i]
    price = row['close']

    strike = round(price / 50) * 50

    # ================= OPTION SYMBOL =================
    ce_symbol = f"NFO:NIFTY{EXPIRY}{int(strike)}CE"
    pe_symbol = f"NFO:NIFTY{EXPIRY}{int(strike)}PE"

    # ================= FETCH OPTION DATA =================
    try:
        opt_data = kite.historical_data(
            instrument_token=kite.ltp(ce_symbol)[ce_symbol]['instrument_token'],
            from_date=row['date'] - datetime.timedelta(minutes=60),
            to_date=row['date'],
            interval="5minute"
        )
    except:
        continue

    df_opt = pd.DataFrame(opt_data)

    if df_opt.empty:
        continue

    df_opt.columns = [col.lower() for col in df_opt.columns]
    df_opt = supertrend(df_opt)

    opt_row = df_opt.iloc[-1]

    # ================= ENTRY =================
    if position is None:

        # CE
        if (
            row['ema9'] > row['ema21'] and
            price > row['ema200'] and
            row['adx'] > 10 and
            opt_row['supertrend'] == True
        ):
            position = "CE"
            entry_price = price
            entry_premium = 120
            capital -= TRADE_CAPITAL

        # PE
        elif (
            row['ema9'] < row['ema21'] and
            price < row['ema200'] and
            row['adx'] > 10 and
            opt_row['supertrend'] == False
        ):
            position = "PE"
            entry_price = price
            entry_premium = 120
            capital -= TRADE_CAPITAL

    # ================= EXIT =================
    elif position:

        premium_move = (price - entry_price) * 0.5

        if premium_move >= TARGET:
            capital += TRADE_CAPITAL + TARGET * LOT_SIZE
            position = None

        elif premium_move <= -SL:
            capital += TRADE_CAPITAL - SL * LOT_SIZE
            position = None

# ================= RESULT =================
print("Final Capital:", capital)
print("PnL:", capital - 20000)
