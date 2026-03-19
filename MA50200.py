import pandas as pd
import yfinance as yf
import requests
import os
import sys

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FAST_MA_LEN = 50
SLOW_MA_LEN = 200
ATR_LEN = 14
ATR_MULT = 3.0
STOCKS = ["BHARTIARTL.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS"]

def send_telegram(message):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        try:
            requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"Telegram Error: {e}")

def run_strategy():
    print(f"🚀 Starting Daily Scan: {pd.Timestamp.now()}")
    
    for symbol in STOCKS:
        print(f"\n🔍 Analyzing {symbol}...")
        
        # 1. Fetch data (Need enough for 200 EMA + some buffer)
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        
        if df.empty or len(df) < SLOW_MA_LEN:
            print(f"⚠️ Not enough data for {symbol}. Skipping.")
            continue

        # 2. Calculate Indicators
        df['EMA50'] = df['Close'].ewm(span=FAST_MA_LEN, adjust=False).mean()
        df['EMA200'] = df['Close'].ewm(span=SLOW_MA_LEN, adjust=False).mean()
        
        # ATR Calculation
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR'] = true_range.rolling(window=ATR_LEN).mean()

        # Get Current and Previous values for Crossover logic
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        price = curr['Close']
        ema50 = curr['EMA50']
        ema200 = curr['EMA200']
        atr = curr['ATR']
        
        # 3. Logic Check
        # Bullish Crossover (50 crosses above 200)
        if prev['EMA50'] <= prev['EMA200'] and ema50 > ema200:
            msg = f"🚀 *BUY SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nEMA50 crossed above EMA200!"
            send_telegram(msg)
            print(f"✅ SIGNAL: {msg}")

        # Bearish Crossunder (50 crosses below 200)
        elif prev['EMA50'] >= prev['EMA200'] and ema50 < ema200:
            msg = f"📉 *EXIT SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nTrend Reversal: EMA50 below EMA200."
            send_telegram(msg)
            print(f"✅ SIGNAL: {msg}")
            
        else:
            trend = "Bullish 🟢" if ema50 > ema200 else "Bearish 🔴"
            print(f"Holding: {symbol} is currently {trend} (No new crossover)")

    print("\n✅ Scan Complete. Exiting.")

if __name__ == "__main__":
    run_strategy()

        time.sleep(60) # Check every minute
    except Exception as e:
        print(f"Loop Error: {e}")
        time.sleep(10)
