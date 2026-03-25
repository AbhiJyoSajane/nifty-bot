from datetime import datetime, timedelta

# ---------------- GLOBAL STATE ----------------
price_history = []

trades_today = 0
morning_trades = 0
afternoon_trades = 0

last_trade_time = None

# ---------------- MOCK DATA (TEMP - will replace with Kite) ----------------
def get_market_data():
    return {
        "price": 100,
        "high": 102,
        "low": 98,
        "volume": 1500
    }

def place_order(action):
    print(f"{datetime.now()} -> ORDER: {action}")

# ---------------- HELPERS ----------------
def avg_range(n=5):
    if len(price_history) < n:
        return 0
    return sum(c["high"] - c["low"] for c in price_history[-n:]) / n

def get_range_high_low(n=10):
    highs = [c["high"] for c in price_history[-n:]]
    lows = [c["low"] for c in price_history[-n:]]
    return max(highs), min(lows)

def get_swing_low():
    return min(c["low"] for c in price_history[-3:])

def get_swing_high():
    return max(c["high"] for c in price_history[-3:])

def is_sideways():
    if len(price_history) < 10:
        return False
    r_high, r_low = get_range_high_low()
    return (r_high - r_low) < avg_range(5) * 3

# ---------------- SESSION ----------------
def get_session():
    now = datetime.now().time()

    m_start = datetime.strptime("09:30", "%H:%M").time()
    m_end = datetime.strptime("11:30", "%H:%M").time()

    a_start = datetime.strptime("14:00", "%H:%M").time()
    a_end = datetime.strptime("15:15", "%H:%M").time()

    if m_start <= now <= m_end:
        return "MORNING"
    elif a_start <= now <= a_end:
        return "AFTERNOON"
    return None

# ---------------- TRADE CONTROL ----------------
def can_trade():
    global trades_today, morning_trades, afternoon_trades, last_trade_time

    if trades_today >= 3:
        return False

    session = get_session()
    if not session:
        return False

    # 5 min cooldown
    if last_trade_time:
        if datetime.now() - last_trade_time < timedelta(minutes=5):
            return False

    if session == "MORNING":
        return morning_trades < 2

    if session == "AFTERNOON":
        if morning_trades == 0:
            return afternoon_trades < 3
        elif morning_trades == 1:
            return afternoon_trades < 2
        else:
            return afternoon_trades < 1

    return False

def record_trade():
    global trades_today, morning_trades, afternoon_trades, last_trade_time

    trades_today += 1
    last_trade_time = datetime.now()

    session = get_session()
    if session == "MORNING":
        morning_trades += 1
    elif session == "AFTERNOON":
        afternoon_trades += 1

# ---------------- STRATEGY ----------------
def run_strategy():
    data = get_market_data()
    price_history.append(data)

    if len(price_history) < 10:
        return

    if not can_trade():
        return

    price = data["price"]
    high = data["high"]
    low = data["low"]

    # -------- SIDEWAYS --------
    if is_sideways():
        r_high, r_low = get_range_high_low()

        if price <= r_low + 0.2:
            place_order("BUY")
            record_trade()

        elif price >= r_high - 0.2:
            place_order("SELL")
            record_trade()

        return

    # -------- TRENDING --------
    if (high - low) > avg_range():

        if price > high - 0.2:
            place_order("BUY")
            record_trade()

        elif price < low + 0.2:
            place_order("SELL")
            record_trade()

    recent_high, recent_low = get_range_high_low(5)

    if price > recent_high:
        place_order("BUY")
        record_trade()

    elif price < recent_low:
        place_order("SELL")
        record_trade()
