import pandas as pd
import numpy as np
from kiteconnect import KiteConnect
from datetime import datetime, timedelta

# --- CONFIGURATION ---
API_KEY = "your_api_key"
ACCESS_TOKEN = "your_access_token"  # Generated via your login flow
STOP_LOSS_PCT = 0.25               # 25% SL on each leg
ENTRY_TIME = "09:20:00"
EXIT_TIME = "15:10:00"
LOT_SIZE = 50

# Initialize Kite
kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

def get_nifty_data(days=30):
    """Fetches historical minute-level data for Nifty 50 Index"""
    instruments = kite.instruments("NSE")
    nifty_token = next(i['instrument_token'] for i in instruments if i['tradingsymbol'] == 'NIFTY 50')
    
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)
    
    # Kite returns max 30 days of minute data in one call
    data = kite.historical_data(nifty_token, from_date, to_date, "minute")
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    return df

def run_backtest():
    df = get_nifty_data(30)
    df['day'] = df['date'].dt.date
    results = []

    for day, day_df in df.groupby('day'):
        # 1. Entry Logic at 09:20
        entry_row = day_df[day_df['date'].dt.strftime('%H:%M:%S') == ENTRY_TIME]
        if entry_row.empty: continue
        
        entry_price = entry_row.iloc[0]['close']
        
        # 2. Simulate Option Premiums
        # At 9:20 AM, a 100-point OTM Nifty option is roughly 0.6% of Nifty value
        initial_premium = (entry_price * 0.006) 
        ce_price = pe_price = initial_premium
        ce_sl = ce_price * (1 + STOP_LOSS_PCT)
        pe_sl = pe_price * (1 + STOP_LOSS_PCT)
        
        ce_active = pe_active = True
        day_pnl = 0

        # 3. Intraday Loop (Checking for SL triggers)
        for _, row in day_df[day_df['date'].dt.strftime('%H:%M:%S') > ENTRY_TIME].iterrows():
            # Calculate price change since entry
            price_change = row['close'] - entry_price
            
            # Simulate Option Movement (Delta ~0.4 for near-OTM)
            current_ce = initial_premium + (price_change * 0.4)
            current_pe = initial_premium - (price_change * 0.4)

            # Check CE Stop Loss
            if ce_active and current_ce >= ce_sl:
                day_pnl -= (ce_sl - initial_premium)
                ce_active = False
            
            # Check PE Stop Loss
            if pe_active and current_pe >= pe_sl:
                day_pnl -= (pe_sl - initial_premium)
                pe_active = False

            # Square off at 3:10 PM
            if row['date'].strftime('%H:%M:%S') >= EXIT_TIME:
                if ce_active: day_pnl += (initial_premium - current_ce)
                if pe_active: day_pnl += (initial_premium - current_pe)
                break
        
        results.append({'Date': day, 'PnL': day_pnl * LOT_SIZE})

    return pd.DataFrame(results)

# --- EXECUTION ---
report = run_backtest()
print(report)
print(f"\nTotal Net Profit: Rs. {report['PnL'].sum():.2f}")
print(f"Win Rate: {(report['PnL'] > 0).mean() * 100:.2f}%")
