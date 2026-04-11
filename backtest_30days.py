import os
from kiteconnect import KiteConnect
import pandas as pd
import matplotlib.pyplot as plt

# ================= CONFIG =================
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
REQUEST_TOKEN = os.getenv("REQUEST_TOKEN")

LOT_SIZE = 50
SL_PERCENT = 0.25
STRIKE_DISTANCE = 100
DAILY_MAX_LOSS = -2000

INITIAL_CAPITAL = 200000

START_DATE = "2024-01-01"
END_DATE = "2024-01-31"
# ==========================================

# ---------- LOGIN ----------
kite = KiteConnect(api_key=API_KEY)

try:
    session = kite.generate_session(REQUEST_TOKEN, api_secret=API_SECRET)
    ACCESS_TOKEN = session["access_token"]
    kite.set_access_token(ACCESS_TOKEN)
    print("✅ Login successful")
except Exception as e:
    print("❌ Login failed:", e)
    exit()

# ---------- FETCH INSTRUMENTS ----------
print("Fetching instruments...")
instruments = pd.DataFrame(kite.instruments("NFO"))

# ---------- FETCH NIFTY DATA ----------
print("Fetching Nifty data...")
nifty = pd.DataFrame(kite.historical_data(
    256265, START_DATE, END_DATE, "minute"
))
nifty['date'] = pd.to_datetime(nifty['date'])
nifty.set_index('date', inplace=True)

capital = INITIAL_CAPITAL
equity_curve = []
trade_log = []

expiry_list = sorted(instruments['expiry'].dropna().unique())

# ---------- BACKTEST ----------
for day, spot_day in nifty.groupby(nifty.index.date):

    daily_pnl = 0

    day_data = spot_day.between_time("09:20", "15:10")
    if len(day_data) == 0:
        continue

    entry_spot = day_data.iloc[0]['close']

    atm = round(entry_spot / 50) * 50
    ce_strike = atm + STRIKE_DISTANCE
    pe_strike = atm - STRIKE_DISTANCE

    # expiry selection
    expiry = next((e for e in expiry_list if e >= pd.Timestamp(day)), None)
    if expiry is None:
        continue

    ce_row = instruments[
        (instruments['name'] == 'NIFTY') &
        (instruments['strike'] == ce_strike) &
        (instruments['instrument_type'] == 'CE') &
        (instruments['expiry'] == expiry)
    ]

    pe_row = instruments[
        (instruments['name'] == 'NIFTY') &
        (instruments['strike'] == pe_strike) &
        (instruments['instrument_type'] == 'PE') &
        (instruments['expiry'] == expiry)
    ]

    if ce_row.empty or pe_row.empty:
        print(f"{day} → Strike not found")
        continue

    ce_token = ce_row.iloc[0]['instrument_token']
    pe_token = pe_row.iloc[0]['instrument_token']

    # Fetch option data
    ce = pd.DataFrame(kite.historical_data(ce_token, START_DATE, END_DATE, "minute"))
    pe = pd.DataFrame(kite.historical_data(pe_token, START_DATE, END_DATE, "minute"))

    ce['date'] = pd.to_datetime(ce['date'])
    pe['date'] = pd.to_datetime(pe['date'])

    ce.set_index('date', inplace=True)
    pe.set_index('date', inplace=True)

    ce = ce.loc[day_data.index]
    pe = pe.loc[day_data.index]

    if len(ce) == 0 or len(pe) == 0:
        print(f"{day} → No option data")
        continue

    ce_entry = ce.iloc[0]['close']
    pe_entry = pe.iloc[0]['close']

    ce_sl = ce_entry * (1 + SL_PERCENT)
    pe_sl = pe_entry * (1 + SL_PERCENT)

    ce_active = True
    pe_active = True

    ce_exit = ce_entry
    pe_exit = pe_entry

    for t in day_data.index:

        ce_price = ce.loc[t]['close']
        pe_price = pe.loc[t]['close']

        # DAILY STOP LOSS
        if daily_pnl <= DAILY_MAX_LOSS:
            print(f"{day} → DAILY SL HIT")
            break

        # CE SL
        if ce_active and ce_price >= ce_sl:
            ce_exit = ce_price
            ce_active = False
            if pe_active:
                pe_sl = pe_entry

        # PE SL
        if pe_active and pe_price >= pe_sl:
            pe_exit = pe_price
            pe_active = False
            if ce_active:
                ce_sl = ce_entry

        # Exit at 3:10
        if t.hour == 15 and t.minute >= 10:
            if ce_active:
                ce_exit = ce_price
            if pe_active:
                pe_exit = pe_price
            break

        # Live P&L
        ce_live = (ce_entry - ce_price) * LOT_SIZE if ce_active else (ce_entry - ce_exit) * LOT_SIZE
        pe_live = (pe_entry - pe_price) * LOT_SIZE if pe_active else (pe_entry - pe_exit) * LOT_SIZE

        daily_pnl = ce_live + pe_live

    ce_pnl = (ce_entry - ce_exit) * LOT_SIZE
    pe_pnl = (pe_entry - pe_exit) * LOT_SIZE

    total_pnl = ce_pnl + pe_pnl
    capital += total_pnl

    equity_curve.append(capital)

    trade_log.append({
        "date": day,
        "expiry": expiry,
        "ce_strike": ce_strike,
        "pe_strike": pe_strike,
        "pnl": total_pnl,
        "capital": capital
    })

    print(f"{day} → P&L: {total_pnl}")

# ---------- RESULTS ----------
results = pd.DataFrame(trade_log)

print("\n========= FINAL RESULT =========")
print(f"Initial Capital : {INITIAL_CAPITAL}")
print(f"Final Capital   : {capital}")
print(f"Total P&L       : {results['pnl'].sum()}")

win = len(results[results['pnl'] > 0])
print(f"Win Rate        : {round(win/len(results)*100,2)}%")

# Save results
results.to_csv("backtest_results.csv", index=False)

# ---------- EQUITY CURVE ----------
plt.figure()
plt.plot(equity_curve)
plt.title("Equity Curve")
plt.xlabel("Trades")
plt.ylabel("Capital")
plt.grid()

plt.savefig("equity_curve.png")
plt.show()
