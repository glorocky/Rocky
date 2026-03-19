import time
import math
from datetime import datetime, timedelta
from collections import deque
import pandas as pd
import yfinance as yf
import requests
import os

# --- TELEGRAM CONFIGURATION ---
# These will be pulled from your GitHub Secrets
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_msg(message):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=payload)
        except Exception as e:
            print(f"Telegram Error: {e}")

# --- STRATEGY PARAMETERS ---
FAST_MA_LEN = 50
SLOW_MA_LEN = 200
USE_ATR_STOP = True
ATR_LEN = 14
ATR_MULT = 3.0
TRADE_VALUE = 3000

# Stock symbols updated for Yahoo Finance (.NS for National Stock Exchange)
STOCKS = ["BHARTIARTL.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS"]
TIMEFRAME = 60  # 1 hour 

stock_data = {}

print("\n" + "="*70)
print("📚 TREND FOLLOWING STRATEGY - MULTI-STOCK (YFINANCE VERSION)")
print("="*70)

# --- REPLACED: DATA FETCHING LOGIC ---
def get_historical_data(symbol, days=30):
    """Fetch historical data using yfinance instead of Groww"""
    try:
        df = yf.download(symbol, period=f"{days}d", interval="60m")
        if df.empty:
            return None
        # Convert yfinance format to the list format the rest of your code expects
        candles = []
        for index, row in df.iterrows():
            candles.append({
                'time': int(index.timestamp() * 1000),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close'])
            })
        return candles
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
        return None

# --- REPLACED: ORDER PLACEMENT (NOW TELEGRAM ALERTS) ---
def place_long_order(price, symbol, stock_symbol):
    """Sends a Telegram Buy Alert instead of an API call"""
    stock_info = stock_data[stock_symbol]
    qty = int(TRADE_VALUE / price) if price > 0 else 1
    msg = f"🚀 *BUY SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nQty: {qty}\nStrategy: EMA Crossover"
    print(f"\n📝 ALERT SENT: {msg}")
    send_telegram_msg(msg)
    stock_info['position'] = 1
    stock_info['entry_price'] = price
    return True

def close_long_order(price, symbol, stock_symbol):
    """Sends a Telegram Sell Alert"""
    stock_info = stock_data[stock_symbol]
    pnl = (price - stock_info['entry_price']) * (TRADE_VALUE/stock_info['entry_price']) if stock_info['entry_price'] > 0 else 0
    msg = f"📉 *EXIT SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nEst. PnL: ₹{pnl:.2f}"
    print(f"\n📝 ALERT SENT: {msg}")
    send_telegram_msg(msg)
    stock_info['position'] = 0
    stock_info['entry_price'] = 0.0
    return True

# --- HELPER FUNCTIONS (KEPT FROM YOUR ORIGINAL) ---
def calculate_ema(prices, period):
    if len(prices) < period: return None
    df = pd.Series(prices)
    return df.ewm(span=period, adjust=False).mean().iloc[-1]

def calculate_atr(highs, lows, closes, period):
    if len(highs) < period + 1: return None
    tr = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1, len(highs))]
    return sum(tr[-period:]) / period

def detect_crossover(f_prev, s_prev, f_curr, s_curr):
    return f_prev <= s_prev and f_curr > s_curr

def detect_crossunder(f_prev, s_prev, f_curr, s_curr):
    return f_prev >= s_prev and f_curr < s_curr

def initialize_stock_data(stock_symbol):
    return {
        'position': 0, 'entry_price': 0.0,
        'recent_closes': deque(maxlen=SLOW_MA_LEN + 10),
        'recent_highs': deque(maxlen=SLOW_MA_LEN + 10),
        'recent_lows': deque(maxlen=SLOW_MA_LEN + 10),
        'fast_ma_history': deque(maxlen=100),
        'slow_ma_history': deque(maxlen=100),
        'atr_history': deque(maxlen=100),
        'current_candle_start': None,
        'current_candle_data': {'close': None},
        'last_status_print': None,
        'initial_entry_checked': False
    }

# --- INITIALIZATION ---
for stock in STOCKS:
    candles = get_historical_data(stock)
    if candles:
        stock_data[stock] = initialize_stock_data(stock)
        info = stock_data[stock]
        for c in candles:
            info['recent_closes'].append(c['close'])
            info['recent_highs'].append(c['high'])
            info['recent_lows'].append(c['low'])
            
            f = calculate_ema(list(info['recent_closes']), FAST_MA_LEN)
            s = calculate_ema(list(info['recent_closes']), SLOW_MA_LEN)
            if f and s:
                info['fast_ma_history'].append(f)
                info['slow_ma_history'].append(s)
        print(f"✅ Loaded {stock}")

# --- MONITORING LOOP ---
print("\n🔄 Monitoring Markets via yfinance...")
while True:
    try:
        for stock in STOCKS:
            ticker = yf.Ticker(stock)
            current_price = ticker.fast_info['last_price']
            info = stock_data[stock]
            
            # Simple Logic: Check if Fast EMA > Slow EMA
            f_curr = calculate_ema(list(info['recent_closes']), FAST_MA_LEN)
            s_curr = calculate_ema(list(info['recent_closes']), SLOW_MA_LEN)
            
            if f_curr and s_curr:
                # Entry Logic
                if info['position'] == 0 and f_curr > s_curr:
                    place_long_order(current_price, stock.split('.')[0], stock)
                
                # Exit Logic (Crossunder or ATR Stop)
                elif info['position'] == 1:
                    if f_curr < s_curr:
                        close_long_order(current_price, stock.split('.')[0], stock)
                    elif USE_ATR_STOP:
                        atr = calculate_atr(list(info['recent_highs']), list(info['recent_lows']), list(info['recent_closes']), ATR_LEN)
                        if atr and current_price < (info['entry_price'] - (ATR_MULT * atr)):
                            print("🚨 Stop Loss Triggered")
                            close_long_order(current_price, stock.split('.')[0], stock)

            # Update recent closes with current price to simulate live candle
            info['recent_closes'].append(current_price)
            print(f"\rMonitoring {stock}: ₹{current_price:.2f} | EMA50: {f_curr:.2f} | EMA200: {s_curr:.2f}", end="")

        time.sleep(60) # Check every minute
    except Exception as e:
        print(f"Loop Error: {e}")
        time.sleep(10)
