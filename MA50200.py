import pandas as pd
import yfinance as yf
import requests
import os
import sys

# --- CONFIGURATION ---
# Ensure these secrets are set in your GitHub Repository
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FAST_MA_LEN = 50
SLOW_MA_LEN = 200
ATR_LEN = 14
STOCKS = ["BHARTIARTL.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS"]

def send_telegram(message):
    """Sends a notification to your Telegram bot"""
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=payload)
        except Exception as e:
            print(f"Telegram Error: {e}")
    else:
        print("⚠️ Telegram Credentials missing. Printing message instead:")
        print(message)

def run_strategy():
    print(f"🚀 Starting Market Scan: {pd.Timestamp.now()}")
    
    for symbol in STOCKS:
        print(f"\n🔍 Analyzing {symbol}...")
        
        # 1. Fetch data (1 year of daily data)
        try:
            df = yf.download(symbol, period="1y", interval="1d", progress=False)
            if df.empty or len(df) < SLOW_MA_LEN:
                print(f"⚠️ Not enough data for {symbol}. Skipping.")
                continue
        except Exception as e:
            print(f"❌ Download Error for {symbol}: {e}")
            continue

        # 2. Calculate Indicators
        # Using .iloc[:, 0] to ensure we get a Series if yf returns a MultiIndex
        close_prices = df['Close'].squeeze() 
        df['EMA50'] = close_prices.ewm(span=FAST_MA_LEN, adjust=False).mean()
        df['EMA200'] = close_prices.ewm(span=SLOW_MA_LEN, adjust=False).mean()
        
        # Get Current and Previous values
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        price = float(curr['Close'])
        ema50 = float(curr['EMA50'])
        ema200 = float(curr['EMA200'])
        
        # 3. Logic Check (Crossover)
        # 50 EMA crosses ABOVE 200 EMA
        if prev['EMA50'] <= prev['EMA200'] and ema50 > ema200:
            msg = f"🚀 *BUY SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nEMA50 crossed ABOVE EMA200!"
            send_telegram(msg)
            print(f"✅ SIGNAL: {msg}")

        # 50 EMA crosses BELOW 200 EMA
        elif prev['EMA50'] >= prev['EMA200'] and ema50 < ema200:
            msg = f"📉 *EXIT SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nTrend Reversal: EMA50 below EMA200."
            send_telegram(msg)
            print(f"✅ SIGNAL: {msg}")
            
        else:
            trend = "Bullish 🟢" if ema50 > ema200 else "Bearish 🔴"
            print(f"Holding: {symbol} is currently {trend} (No new crossover)")

    print("\n✅ All stocks scanned. Process complete.")

if __name__ == "__main__":
    run_strategy()
