import pandas as pd
from kiteconnect import KiteConnect
from datetime import datetime, timedelta

# --- 1. CREDENTIALS ---
# Get these from https://kite.trade/developer/dashboard
API_KEY = "your_api_key"
API_SECRET = "your_api_secret"

# 2. GETTING THE REQUEST TOKEN:
# Login here: https://kite.trade/connect/login?api_key=YOUR_API_KEY
# Copy the 'request_token=' value from the URL after redirecting.
REQUEST_TOKEN = "paste_your_request_token_here" 

# --- 2. INITIALIZE & AUTHENTICATE ---
kite = KiteConnect(api_key=API_KEY)

try:
    # Exchange Request Token for Access Token
    data = kite.generate_session(REQUEST_TOKEN, api_secret=API_SECRET)
    access_token = data["access_token"]
    kite.set_access_token(access_token)
    print(f"✅ Authentication Successful! Access Token: {access_token}")
except Exception as e:
    print(f"❌ Auth Failed: {e}")
    print("Check if your Request Token is expired (they last only a few minutes) or already used.")
    exit()

# --- 3. BACKTEST LOGIC ---
def run_30_day_backtest():
    print("🔄 Fetching 30 days of Nifty 50 data...")
    
    # Get Nifty 50 Instrument Token
    instruments = kite.instruments("NSE")
    nifty_token = next(i['instrument_token'] for i in instruments if i['tradingsymbol'] == 'NIFTY 50')

    # Fetch Data
    to_date = datetime.now()
    from_date = to_date - timedelta(days=30)
    
    try:
        records = kite.historical_data(nifty_token, from_date, to_date, "minute")
    except Exception as e:
        print(f"❌ Historical Data Error: {e}")
        print("Tip: Ensure 'Historical API' is subscribed in your Kite Dashboard.")
        return

    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    df['day'] = df['date'].dt.date
    
    results = []
    lot_size = 50
    sl_pct = 0.25 # 25% Stop Loss

    for day, day_df in df.groupby('day'):
        # Entry at 09:20
        entry_row = day_df[day_df['date'].dt.strftime('%H:%M') == '09:20']
        if entry_row.empty: continue
        
        spot_entry = entry_row.iloc[0]['close']
        
        # Simulate combined Premium (Approx 1.2% of Spot for a Strangle)
        initial_premium = spot_entry * 0.012 
        sl_value = initial_premium * (1 + sl_pct)
        
        # Exit at 15:10
        exit_row = day_df[day_df['date'].dt.strftime('%H:%M') == '15:10']
        if exit_row.empty: exit_row = day_df.iloc[-1:]
        
        spot_exit = exit_row.iloc[0]['close']
        
        # Simple Delta-based PnL simulation
        # If market moves > 1.2%, assume SL hit. Otherwise, assume 40% Theta decay.
        price_move_pct = abs(spot_exit - spot_entry) / spot_entry
        
        if price_move_pct > 0.012: 
            day_pnl = -(initial_premium * sl_pct) # Loss capped at SL
        else:
            day_pnl = initial_premium * 0.40 # Profit from decay
            
        results.append({'Date': day, 'PnL': day_pnl * lot_size})

    report = pd.DataFrame(results)
    print("\n" + "="*30)
    print(report)
    print("="*30)
    print(f"TOTAL 30-DAY PNL: ₹{report['PnL'].sum():.2f}")
    print(f"WIN RATE: {(report['PnL'] > 0).mean()*100:.2f}%")

if __name__ == "__main__":
    run_30_day_backtest()
