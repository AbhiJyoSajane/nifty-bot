//@version=5
strategy("Inside Candle Breakout (Backtest Ready)", overlay=true,
     default_qty_type=strategy.percent_of_equity,
     default_qty_value=100)

// ===== Identify Inside Candle =====
inside = high < high[1] and low > low[1]

// Store Mother Candle Levels
motherHigh = high[1]
motherLow  = low[1]

// ===== Entry Conditions =====
// Breakout happens AFTER inside candle forms
buyCondition  = inside[1] and close > motherHigh[1]
sellCondition = inside[1] and close < motherLow[1]

// ===== Execute Entries =====
if (buyCondition)
    strategy.entry("BUY", strategy.long)

if (sellCondition)
    strategy.entry("SELL", strategy.short)

// ===== Stop Loss =====
longSL  = motherLow[1]
shortSL = motherHigh[1]

// ===== Risk Reward (1:2) =====
longRisk  = strategy.position_avg_price - longSL
shortRisk = shortSL - strategy.position_avg_price

longTarget  = strategy.position_avg_price + (longRisk * 2)
shortTarget = strategy.position_avg_price - (shortRisk * 2)

// ===== Exit Logic =====
strategy.exit("Exit Buy",  from_entry="BUY",  stop=longSL,  limit=longTarget)
strategy.exit("Exit Sell", from_entry="SELL", stop=shortSL, limit=shortTarget)

// ===== Plot Levels =====
plot(motherHigh, color=color.green, title="Mother High")
plot(motherLow, color=color.red, title="Mother Low")
