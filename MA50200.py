import time
import math
from datetime import datetime, timedelta
from collections import deque
#from growwapi import GrowwAPI
import statistics

# Configuration
#api_key = ""
#secret = ""

# Strategy parameters (from Pine Script trend.txt)
FAST_MA_LEN = 50   # Fast EMA length
SLOW_MA_LEN = 200  # Slow EMA length
USE_ATR_STOP = True  # Use ATR-based stop-loss
ATR_LEN = 14       # ATR length
ATR_MULT = 3.0     # ATR stop multiplier

# Trading parameters
TRADE_VALUE = 3000  # Trade ₹3000 worth per stock

# Stock symbols - Add your stocks here
STOCKS = [
    "NSE_BHARTIARTL",
    "NSE_RELIANCE",
    "NSE_TCS",
    "NSE_INFY",
    # Add more stocks as needed
]
TIMEFRAME = 60  # 1 hour candles (can be adjusted)

# Per-stock data tracking
stock_data = {}  # Will be initialized for each stock

# Initialize API
#access_token = GrowwAPI.get_access_token(api_key=api_key, secret=secret)
#groww = GrowwAPI(access_token)
#print("✅ Ready to Groww")

# Product type for trading
PRODUCT_TYPE = groww.PRODUCT_MIS

print("\n" + "="*70)
print("📚 TREND FOLLOWING STRATEGY - MULTI-STOCK")
print("="*70)
print(f"   Stocks: {len(STOCKS)} stocks")
for stock in STOCKS:
    print(f"     • {stock.replace('NSE_', '')}")
print(f"   Fast EMA: {FAST_MA_LEN}")
print(f"   Slow EMA: {SLOW_MA_LEN}")
print(f"   ATR Stop: {'Enabled' if USE_ATR_STOP else 'Disabled'} (Length: {ATR_LEN}, Multiplier: {ATR_MULT})")
print(f"   Trade Value per stock: ₹{TRADE_VALUE}")
print("="*70)
print("")

def get_historical_data(symbol, days=30):
    """Fetch historical candle data"""
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    try:
        # Method 1: get_historical_candle_data
        try:
            data = groww.get_historical_candle_data(
                trading_symbol=symbol.replace("NSE_", ""),
                exchange=groww.EXCHANGE_NSE,
                segment=groww.SEGMENT_CASH,
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
                interval_in_minutes=TIMEFRAME
            )
            return data
        except Exception as e1:
            # Method 2: get_historical_candles
            try:
                instrument = groww.get_instrument_by_exchange_and_trading_symbol(
                    exchange=groww.EXCHANGE_NSE,
                    trading_symbol=symbol.replace("NSE_", "")
                )
                groww_symbol = instrument.get('groww_symbol')
                if groww_symbol:
                    if TIMEFRAME == 1:
                        interval_str = "1minute"
                    elif TIMEFRAME == 5:
                        interval_str = "5minute"
                    elif TIMEFRAME == 15:
                        interval_str = "15minute"
                    elif TIMEFRAME == 30:
                        interval_str = "30minute"
                    elif TIMEFRAME == 60:
                        interval_str = "1hour"
                    else:
                        interval_str = f"{TIMEFRAME}minute"
                    
                    data = groww.get_historical_candles(
                        exchange=groww.EXCHANGE_NSE,
                        segment=groww.SEGMENT_CASH,
                        groww_symbol=groww_symbol,
                        start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                        end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
                        candle_interval=interval_str
                    )
                    return data
                else:
                    raise Exception("groww_symbol not found")
            except Exception as e2:
                print(f"❌ All methods failed for {symbol}. Errors: {e1}, {e2}")
                return None
    except Exception as e:
        print(f"Error fetching historical data for {symbol}: {e}")
        return None

def normalize_timestamp(ts):
    """Normalize timestamp to milliseconds"""
    if isinstance(ts, (int, float)):
        if ts > 1e12:
            return int(ts)
        else:
            return int(ts * 1000)
    elif isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return int(dt.timestamp() * 1000)
        except:
            return None
    return None

def extract_candle_data(candle):
    """Extract OHLC data from candle"""
    if isinstance(candle, list):
        if len(candle) >= 5:
            ts = candle[0]
            open_price = candle[1]
            high = candle[2]
            low = candle[3]
            close = candle[4]
            return ts, open_price, high, low, close
        return None, None, None, None, None
    elif isinstance(candle, dict):
        ts = candle.get('time') or candle.get('timestamp') or candle.get('t')
        open_price = candle.get('open') or candle.get('o')
        high = candle.get('high') or candle.get('h')
        low = candle.get('low') or candle.get('l')
        close = candle.get('close') or candle.get('c')
        return ts, open_price, high, low, close
    return None, None, None, None, None

def extract_candles(response):
    """Extract candles from API response"""
    if isinstance(response, dict):
        if 'candles' in response:
            return response['candles']
        elif 'data' in response:
            if isinstance(response['data'], dict):
                return response['data'].get('candles', [])
            elif isinstance(response['data'], list):
                return response['data']
        elif 'result' in response:
            return response['result'].get('candles', [])
    elif isinstance(response, list):
        return response
    return []

def calculate_ema(prices, period):
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return None
    
    # Initialize with SMA
    ema = sum(prices[:period]) / period
    multiplier = 2.0 / (period + 1)
    
    # Calculate EMA for remaining prices
    for price in prices[period:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema

def calculate_atr(highs, lows, closes, period):
    """Calculate Average True Range"""
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return None
    
    true_ranges = []
    for i in range(1, len(highs)):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i-1])
        tr3 = abs(lows[i] - closes[i-1])
        true_ranges.append(max(tr1, tr2, tr3))
    
    if len(true_ranges) < period:
        return None
    
    # Calculate ATR as SMA of true ranges
    atr = sum(true_ranges[-period:]) / period
    return atr

def detect_crossover(fast_ma_prev, slow_ma_prev, fast_ma_curr, slow_ma_curr):
    """Detect if fast MA crossed above slow MA"""
    if fast_ma_prev is None or slow_ma_prev is None or fast_ma_curr is None or slow_ma_curr is None:
        return False
    return fast_ma_prev <= slow_ma_prev and fast_ma_curr > slow_ma_curr

def detect_crossunder(fast_ma_prev, slow_ma_prev, fast_ma_curr, slow_ma_curr):
    """Detect if fast MA crossed below slow MA"""
    if fast_ma_prev is None or slow_ma_prev is None or fast_ma_curr is None or slow_ma_curr is None:
        return False
    return fast_ma_prev >= slow_ma_prev and fast_ma_curr < slow_ma_curr

def calculate_quantity(price, trade_value):
    """Calculate quantity based on price and trade value"""
    if price <= 0:
        return 0
    quantity = int(trade_value / price)
    return max(1, quantity)

def place_long_order(price, symbol, stock_symbol):
    """Place LONG order for a specific stock"""
    stock_info = stock_data[stock_symbol]
    try:
        qty = calculate_quantity(price, TRADE_VALUE)
        
        print(f"\n📝 [{stock_symbol.replace('NSE_', '')}] Placing LONG order:")
        print(f"   • BUY {qty} shares of {symbol} @ ₹{price:.2f} (Value: ₹{qty * price:.2f})")
        
        order = groww.place_order(
            validity=groww.VALIDITY_DAY,
            exchange=groww.EXCHANGE_NSE,
            order_type=groww.ORDER_TYPE_MARKET,
            product=PRODUCT_TYPE,
            quantity=qty,
            segment=groww.SEGMENT_CASH,
            trading_symbol=symbol,
            transaction_type=groww.TRANSACTION_TYPE_BUY,
            price=0.0
        )
        print(f"   ✅ Order placed: {order.get('groww_order_id', 'N/A')}")
        stock_info['position'] = 1
        stock_info['entry_price'] = price
        return True
    except Exception as e:
        print(f"   ❌ Error placing order: {e}")
        return False

def close_long_order(price, symbol, stock_symbol):
    """Close LONG position for a specific stock"""
    stock_info = stock_data[stock_symbol]
    try:
        qty = calculate_quantity(stock_info['entry_price'] if stock_info['entry_price'] > 0 else price, TRADE_VALUE)
        
        print(f"\n📝 [{stock_symbol.replace('NSE_', '')}] Closing LONG position:")
        print(f"   • SELL {qty} shares of {symbol} @ ₹{price:.2f}")
        
        order = groww.place_order(
            validity=groww.VALIDITY_DAY,
            exchange=groww.EXCHANGE_NSE,
            order_type=groww.ORDER_TYPE_MARKET,
            product=PRODUCT_TYPE,
            quantity=qty,
            segment=groww.SEGMENT_CASH,
            trading_symbol=symbol,
            transaction_type=groww.TRANSACTION_TYPE_SELL,
            price=0.0
        )
        print(f"   ✅ Order placed: {order.get('groww_order_id', 'N/A')}")
        
        pnl = (price - stock_info['entry_price']) * qty if stock_info['entry_price'] > 0 else 0
        print(f"   📊 P&L: ₹{pnl:.2f}")
        
        stock_info['position'] = 0
        stock_info['entry_price'] = 0.0
        return True
    except Exception as e:
        print(f"   ❌ Error closing position: {e}")
        return False

def initialize_stock_data(stock_symbol):
    """Initialize data structure for a stock"""
    return {
        'position': 0,  # 1 = long, 0 = flat
        'entry_price': 0.0,
        'recent_closes': deque(maxlen=SLOW_MA_LEN + 100),
        'recent_highs': deque(maxlen=SLOW_MA_LEN + 100),
        'recent_lows': deque(maxlen=SLOW_MA_LEN + 100),
        'fast_ma_history': deque(maxlen=1000),
        'slow_ma_history': deque(maxlen=1000),
        'atr_history': deque(maxlen=1000),
        'current_candle_start': None,
        'current_candle_data': {'open': None, 'high': None, 'low': None, 'close': None},
        'last_status_print': None,
        'initial_entry_checked': False,
    }

def process_stock_historical_data(stock_symbol):
    """Fetch and process historical data for a stock"""
    print(f"\n📊 Fetching historical data for {stock_symbol.replace('NSE_', '')}...")
    hist_data = get_historical_data(stock_symbol, days=30)
    
    if not hist_data:
        print(f"❌ Failed to fetch historical data for {stock_symbol}")
        return False
    
    candles = extract_candles(hist_data)
    if not candles:
        print(f"❌ No candles found for {stock_symbol}")
        return False
    
    # Process candles
    processed_candles = []
    for candle in candles:
        ts, open_p, high, low, close = extract_candle_data(candle)
        if ts and close is not None:
            normalized_ts = normalize_timestamp(ts)
            if normalized_ts:
                processed_candles.append({
                    'time': normalized_ts,
                    'open': open_p if open_p else close,
                    'high': high if high else close,
                    'low': low if low else close,
                    'close': close
                })
    
    processed_candles.sort(key=lambda x: x['time'])
    print(f"✅ Fetched {len(processed_candles)} candles for {stock_symbol.replace('NSE_', '')}")
    
    if len(processed_candles) < SLOW_MA_LEN:
        print(f"⚠️  Warning: Only {len(processed_candles)} candles, need {SLOW_MA_LEN} for slow MA")
        if len(processed_candles) < 50:
            print(f"❌ Need at least 50 candles for {stock_symbol}")
            return False
    
    # Build price series
    closes = [c['close'] for c in processed_candles]
    highs = [c['high'] for c in processed_candles]
    lows = [c['low'] for c in processed_candles]
    
    # Initialize stock data
    stock_data[stock_symbol] = initialize_stock_data(stock_symbol)
    stock_info = stock_data[stock_symbol]
    
    # Populate recent data from historical
    stock_info['recent_closes'] = deque(closes[-SLOW_MA_LEN:], maxlen=SLOW_MA_LEN + 100)
    stock_info['recent_highs'] = deque(highs[-SLOW_MA_LEN:], maxlen=SLOW_MA_LEN + 100)
    stock_info['recent_lows'] = deque(lows[-SLOW_MA_LEN:], maxlen=SLOW_MA_LEN + 100)
    
    # Calculate EMAs and ATR for historical data
    print(f"📈 Processing historical data for {stock_symbol.replace('NSE_', '')}...")
    for i in range(max(FAST_MA_LEN, SLOW_MA_LEN, ATR_LEN + 1), len(processed_candles)):
        # Calculate EMAs
        fast_ma = calculate_ema(closes[:i+1], FAST_MA_LEN)
        slow_ma = calculate_ema(closes[:i+1], SLOW_MA_LEN)
        
        # Calculate ATR
        atr = calculate_atr(highs[:i+1], lows[:i+1], closes[:i+1], ATR_LEN)
        
        if fast_ma and slow_ma:
            stock_info['fast_ma_history'].append(fast_ma)
            stock_info['slow_ma_history'].append(slow_ma)
            
            if atr:
                stock_info['atr_history'].append(atr)
    
    return True

# Process all stocks
print(f"\n📊 Fetching historical data for {len(STOCKS)} stocks...")

for stock in STOCKS:
    if not process_stock_historical_data(stock):
        print(f"⚠️  Skipping {stock} due to data issues")
        # Remove from STOCKS list if data fetch failed
        if stock in stock_data:
            del stock_data[stock]

# Filter out stocks that failed to initialize
STOCKS = [s for s in STOCKS if s in stock_data]

if len(STOCKS) == 0:
    print("❌ No stocks successfully initialized. Exiting.")
    exit(1)

print(f"\n✅ Historical analysis complete for {len(STOCKS)} stocks. Starting live monitoring...")
for stock in STOCKS:
    stock_info = stock_data[stock]
    print(f"   {stock.replace('NSE_', '')}: Position {stock_info['position']} (1=Long, 0=Flat)")

# Live monitoring
print(f"\n🔄 Starting live data monitoring for {len(STOCKS)} stocks...")
print(f"   Strategy: Trend Following (EMA Crossover)")
print(f"   Fast EMA: {FAST_MA_LEN} | Slow EMA: {SLOW_MA_LEN}")
print(f"   Trade Value per stock: ₹{TRADE_VALUE}\n")

def round_to_timeframe(timestamp):
    """Round timestamp to nearest TIMEFRAME-minute interval"""
    dt = datetime.fromtimestamp(timestamp / 1000) if isinstance(timestamp, (int, float)) else timestamp
    minutes = (dt.minute // TIMEFRAME) * TIMEFRAME
    rounded = dt.replace(minute=minutes, second=0, microsecond=0)
    return int(rounded.timestamp() * 1000)

def get_trading_day_progress():
    """Calculate progress of trading day from 9:15 AM to 3:30 PM"""
    now = datetime.now()
    
    # Set trading hours (9:15 AM to 3:30 PM)
    today = now.date()
    market_open = datetime.combine(today, datetime.min.time().replace(hour=9, minute=15))
    market_close = datetime.combine(today, datetime.min.time().replace(hour=15, minute=30))
    
    # If before market open, show 0%
    if now < market_open:
        return 0.0, "Pre-market"
    # If after market close, show 100%
    if now > market_close:
        return 100.0, "Market closed"
    
    # Calculate progress
    total_duration = (market_close - market_open).total_seconds()
    elapsed = (now - market_open).total_seconds()
    progress = (elapsed / total_duration) * 100
    
    return progress, "Trading"

def format_progress_bar(progress, width=20):
    """Format a progress bar"""
    filled = int(width * progress / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {progress:.1f}%"

def print_live_status(stock_symbol, current_price, recent_closes, recent_highs, recent_lows, fast_ma_history, slow_ma_history, atr_history, position, entry_price, last_print_time=None):
    """Print current status with live updates for a stock"""
    stock_name = stock_symbol.replace('NSE_', '')
    if current_price is None:
        print(f"\r[{stock_name}] ❌ No price data", end="", flush=True)
        return last_print_time
    
    now = datetime.now()
    
    # Print every 2 seconds to avoid too frequent updates
    if last_print_time is not None and (now - last_print_time).total_seconds() < 2:
        return last_print_time
    
    # Get trading day progress
    progress, market_status = get_trading_day_progress()
    progress_bar = format_progress_bar(progress)
    timestamp_str = now.strftime("%H:%M:%S")
    
    # Calculate indicators - show partial values when available
    fast_ma = None
    slow_ma = None
    slow_ma_partial = None
    atr = None
    
    # Calculate Fast MA if we have enough data
    if len(recent_closes) >= FAST_MA_LEN:
        fast_ma = calculate_ema(list(recent_closes), FAST_MA_LEN)
    
    # Calculate Slow MA if we have enough data (full calculation)
    if len(recent_closes) >= SLOW_MA_LEN:
        slow_ma = calculate_ema(list(recent_closes), SLOW_MA_LEN)
        atr = calculate_atr(list(recent_highs), list(recent_lows), list(recent_closes), ATR_LEN) if USE_ATR_STOP else None
    # Calculate partial Slow MA if we have some data (for display purposes)
    elif len(recent_closes) >= FAST_MA_LEN:
        # Calculate Slow MA using all available candles as period (will approximate 200-period EMA once we have 200 candles)
        # This gives a value to display, though it's not the exact 200-period EMA until we have 200 candles
        slow_ma_partial = calculate_ema(list(recent_closes), len(recent_closes))
    
    # Build status message with available data
    if len(recent_closes) < FAST_MA_LEN:
        # Not enough data for even fast MA
        print(f"\r[{stock_name}] {timestamp_str} | {progress_bar} ({market_status}) | ⏳ Building: {len(recent_closes)}/{FAST_MA_LEN} | Price: ₹{current_price:.2f} | {'LONG' if position == 1 else 'FLAT'}", end="", flush=True)
        return now
    elif len(recent_closes) < SLOW_MA_LEN:
        # Have fast MA but not slow MA yet - show partial Slow MA
        fast_ma_str = f"Fast: {fast_ma:.2f}" if fast_ma else "Fast: ..."
        slow_ma_str = ""
        if slow_ma_partial is not None:
            progress_pct = (len(recent_closes) / SLOW_MA_LEN) * 100
            slow_ma_str = f" | Slow: {slow_ma_partial:.2f} ({len(recent_closes)}/{SLOW_MA_LEN}, {progress_pct:.0f}%)"
        else:
            slow_ma_str = f" | Slow: ... ({len(recent_closes)}/{SLOW_MA_LEN})"
        print(f"\r[{stock_name}] {timestamp_str} | {progress_bar} ({market_status}) | ⏳ Building | Price: ₹{current_price:.2f} | {fast_ma_str}{slow_ma_str} | {'LONG' if position == 1 else 'FLAT'}", end="", flush=True)
        return now
    
    # Both MAs available
    if fast_ma is None or slow_ma is None:
        print(f"\r[{stock_name}] {timestamp_str} | {progress_bar} ({market_status}) | ⏳ Calculating... | Price: ₹{current_price:.2f} | {'LONG' if position == 1 else 'FLAT'}", end="", flush=True)
        return now
    
    # Determine trend direction
    trend = "🟢 BULLISH" if fast_ma > slow_ma else "🔴 BEARISH"
    
    # Position description
    pos_desc = "🟢 LONG" if position == 1 else "⚪ FLAT"
    
    # Explain why position is flat
    reason_str = ""
    if position == 0:
        if fast_ma > slow_ma:
            # Check if we have previous MA values to see if crossover already happened
            if len(fast_ma_history) > 0 and len(slow_ma_history) > 0:
                fast_prev = fast_ma_history[-1] if len(fast_ma_history) > 0 else None
                slow_prev = slow_ma_history[-1] if len(slow_ma_history) > 0 else None
                if fast_prev is not None and slow_prev is not None:
                    if fast_prev > slow_prev:
                        reason_str = " (Fast > Slow, but crossover already happened - waiting for next candle close to enter)"
                    else:
                        reason_str = " (Fast just crossed above Slow - will enter at next candle close)"
                else:
                    reason_str = " (Fast > Slow, waiting for crossover confirmation at candle close)"
            else:
                reason_str = " (Fast > Slow, but need previous candle data to confirm crossover)"
        else:
            reason_str = " (Fast < Slow, no entry signal - waiting for Fast to cross above Slow)"
    
    # Calculate P&L if in position
    pnl_str = ""
    if position == 1 and entry_price > 0:
        pnl = (current_price - entry_price) / entry_price * 100
        pnl_abs = current_price - entry_price
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        pnl_str = f" | Entry: ₹{entry_price:.2f} | P&L: {pnl_emoji} {pnl:+.2f}% (₹{pnl_abs:+.2f})"
    
    # ATR stop info
    atr_str = ""
    if USE_ATR_STOP and atr and position == 1 and entry_price > 0:
        stop_price = entry_price - (ATR_MULT * atr)
        stop_dist = current_price - stop_price
        stop_pct = (stop_dist / current_price) * 100 if current_price > 0 else 0
        atr_str = f" | Stop: ₹{stop_price:.2f} ({stop_pct:.2f}% away)"
    
    # Print status with MA values (compact format for multi-stock)
    print(f"\r[{stock_name}] {timestamp_str} | {trend} | ₹{current_price:.2f} | Fast: {fast_ma:.2f} | Slow: {slow_ma:.2f} | {pos_desc}{reason_str[:30] if reason_str else ''}{pnl_str[:40] if pnl_str else ''}{atr_str[:30] if atr_str else ''}", end="", flush=True)
    return now

# Extract price helper function
def extract_ltp(response, symbol=None):
    if isinstance(response, dict):
        if symbol and symbol in response:
            symbol_data = response[symbol]
            if isinstance(symbol_data, dict):
                return symbol_data.get('ltp') or symbol_data.get('last_price') or symbol_data.get('price')
            elif isinstance(symbol_data, (int, float)):
                return symbol_data
        if 'data' in response:
            data = response['data']
            if isinstance(data, list) and len(data) > 0:
                return data[0].get('ltp') or data[0].get('last_price')
        if 'ltp' in response:
            return response['ltp']
        if 'last_price' in response:
            return response['last_price']
    return None

while True:
    try:
        # Process each stock
        for stock_symbol in STOCKS:
            stock_info = stock_data[stock_symbol]
            
            # Get current LTP for this stock
            ltp = groww.get_ltp(
                segment=groww.SEGMENT_CASH,
                exchange_trading_symbols=(stock_symbol,)
            )
            
            current_price = extract_ltp(ltp, stock_symbol)
            
            if current_price is None:
                continue  # Skip this stock if no price data
            
            # Print live status updates continuously
            stock_info['last_status_print'] = print_live_status(
                stock_symbol, current_price,
                stock_info['recent_closes'], stock_info['recent_highs'], stock_info['recent_lows'],
                stock_info['fast_ma_history'], stock_info['slow_ma_history'], stock_info['atr_history'],
                stock_info['position'], stock_info['entry_price'], stock_info['last_status_print']
            )
            
            # Check for initial entry on boot (if Fast > Slow and we're flat)
            if not stock_info['initial_entry_checked'] and stock_info['position'] == 0:
                recent_closes = stock_info['recent_closes']
                if len(recent_closes) >= FAST_MA_LEN:
                    fast_ma_check = calculate_ema(list(recent_closes), FAST_MA_LEN)
                    if len(recent_closes) >= SLOW_MA_LEN:
                        slow_ma_check = calculate_ema(list(recent_closes), SLOW_MA_LEN)
                    elif len(recent_closes) >= FAST_MA_LEN:
                        slow_ma_check = calculate_ema(list(recent_closes), len(recent_closes))
                    else:
                        slow_ma_check = None
                    
                    if fast_ma_check and slow_ma_check and fast_ma_check > slow_ma_check:
                        print(f"\n🚨 [{stock_symbol.replace('NSE_', '')}] INITIAL ENTRY (Fast > Slow on boot)")
                        symbol = stock_symbol.replace("NSE_", "")
                        place_long_order(current_price, symbol, stock_symbol)
                        stock_info['initial_entry_checked'] = True
                    elif fast_ma_check and slow_ma_check:
                        stock_info['initial_entry_checked'] = True
            
            # Get current timestamp and round to TIMEFRAME-minute interval
            now = datetime.now()
            candle_timestamp = round_to_timeframe(int(now.timestamp() * 1000))
            
            # Check if we have a new candle
            if stock_info['current_candle_start'] != candle_timestamp:
                # Previous candle has closed - process it
                if stock_info['current_candle_start'] is not None and stock_info['current_candle_data']['close'] is not None:
                    prev_close = stock_info['current_candle_data']['close']
                    prev_high = stock_info['current_candle_data'].get('high', prev_close)
                    prev_low = stock_info['current_candle_data'].get('low', prev_close)
                    
                    # Add to recent data
                    stock_info['recent_closes'].append(prev_close)
                    stock_info['recent_highs'].append(prev_high)
                    stock_info['recent_lows'].append(prev_low)
                    
                    # Calculate indicators
                    recent_closes = stock_info['recent_closes']
                    if len(recent_closes) >= SLOW_MA_LEN:
                        fast_ma = calculate_ema(list(recent_closes), FAST_MA_LEN)
                        slow_ma = calculate_ema(list(recent_closes), SLOW_MA_LEN)
                        atr = calculate_atr(list(stock_info['recent_highs']), list(stock_info['recent_lows']), list(recent_closes), ATR_LEN) if USE_ATR_STOP else None
                        
                        if fast_ma and slow_ma:
                            # Store previous values for crossover detection
                            fast_ma_prev = stock_info['fast_ma_history'][-1] if len(stock_info['fast_ma_history']) > 0 else None
                            slow_ma_prev = stock_info['slow_ma_history'][-1] if len(stock_info['slow_ma_history']) > 0 else None
                            
                            # Update history
                            stock_info['fast_ma_history'].append(fast_ma)
                            stock_info['slow_ma_history'].append(slow_ma)
                            if atr:
                                stock_info['atr_history'].append(atr)
                            
                            # Check for signals
                            timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
                            print()  # New line before candle close info
                            print(f"[{stock_symbol.replace('NSE_', '')}] {timestamp_str} | [CANDLE CLOSE] Price: ₹{prev_close:.2f} | Fast MA: {fast_ma:.2f} | Slow MA: {slow_ma:.2f}", end="")
                            if atr:
                                stop_price = prev_close - (ATR_MULT * atr)
                                print(f" | ATR Stop: ₹{stop_price:.2f}", end="")
                            print(f" | Position: {'LONG' if stock_info['position'] == 1 else 'FLAT'}")
                            
                            # Check for crossover (LONG entry) - AT CANDLE CLOSE ONLY
                            if stock_info['position'] == 0:  # Only check entry if we're flat
                                entry_signal = False
                                signal_reason = ""
                                
                                if fast_ma_prev is not None and slow_ma_prev is not None:
                                    if detect_crossover(fast_ma_prev, slow_ma_prev, fast_ma, slow_ma):
                                        entry_signal = True
                                        signal_reason = "Crossover Detected"
                                    elif fast_ma > slow_ma:
                                        entry_signal = True
                                        signal_reason = "Fast > Slow (crossover already happened, entering now)"
                                elif fast_ma > slow_ma:
                                    entry_signal = True
                                    signal_reason = "Fast > Slow (entering on first available candle)"
                                
                                if entry_signal:
                                    print(f"\n🚨 [{stock_symbol.replace('NSE_', '')}] LONG ENTRY ({signal_reason} - At Candle Close)")
                                    symbol = stock_symbol.replace("NSE_", "")
                                    place_long_order(prev_close, symbol, stock_symbol)
                            
                            # Check for crossunder (EXIT) - AT CANDLE CLOSE ONLY
                            if fast_ma_prev is not None and slow_ma_prev is not None:
                                if detect_crossunder(fast_ma_prev, slow_ma_prev, fast_ma, slow_ma) and stock_info['position'] == 1:
                                    print(f"\n🚨 [{stock_symbol.replace('NSE_', '')}] EXIT SIGNAL (Trend Reversal - At Candle Close)")
                                    symbol = stock_symbol.replace("NSE_", "")
                                    close_long_order(prev_close, symbol, stock_symbol)
                            
                            # Check ATR stop-loss - AT CANDLE CLOSE ONLY
                            if USE_ATR_STOP and stock_info['position'] == 1 and atr:
                                stop_price = stock_info['entry_price'] - (ATR_MULT * atr) if stock_info['entry_price'] > 0 else prev_close - (ATR_MULT * atr)
                                if prev_close <= stop_price:
                                    print(f"\n🚨 [{stock_symbol.replace('NSE_', '')}] STOP-LOSS TRIGGERED (At Candle Close) @ ₹{stop_price:.2f}")
                                    symbol = stock_symbol.replace("NSE_", "")
                                    close_long_order(prev_close, symbol, stock_symbol)
                
                # Start new candle
                stock_info['current_candle_start'] = candle_timestamp
                stock_info['current_candle_data'] = {
                    'open': current_price,
                    'high': current_price,
                    'low': current_price,
                    'close': current_price
                }
            else:
                # Update current candle (but don't trade until candle closes)
                stock_info['current_candle_data']['close'] = current_price
                stock_info['current_candle_data']['high'] = max(stock_info['current_candle_data'].get('high', current_price), current_price)
                stock_info['current_candle_data']['low'] = min(stock_info['current_candle_data'].get('low', current_price), current_price)
        
        # Sleep before next check (after processing all stocks)
        time.sleep(5)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping live monitoring...")
        break
    except Exception as e:
        print(f"\n❌ Error in live monitoring: {e}")
        time.sleep(10)
