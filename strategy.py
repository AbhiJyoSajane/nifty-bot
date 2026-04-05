from kiteconnect import KiteConnect
from datetime import datetime, timedelta

# 🔑 Your credentials
API_KEY = "btj1h6qbwop4gah2"
ACCESS_TOKEN = "6Usfkw0Q3rKm18F1uIX5Q6VTtKZvdHEO"

# 🔌 Connect
kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

print("✅ Connected for strategy")

# 📅 Get last 30 days data (5 min)
to_date = datetime.now()
from_date = to_date - timedelta(days=30)

data = kite.historical_data(
    instrument_token=256265,  # NIFTY 50
    from_date=from_date,
    to_date=to_date,
    interval="5minute"
)

print("Candles fetched:", len(data))

# 🧠 Simple strategy (sample)
# Buy if close > open, Sell if close < open

profit = 0

for candle in data:
    open_price = candle["open"]
    close_price = candle["close"]

    if close_price > open_price:
        profit += (close_price - open_price)
    else:
        profit += (open_price - close_price)

print("📊 Total Points Profit:", round(profit, 2))
