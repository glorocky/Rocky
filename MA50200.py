import pandas as pd
import yfinance as yf
import requests
import os

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FAST_MA_LEN = 50
SLOW_MA_LEN = 200
STOCKS = ["BHARTIARTL.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS"]

def send_telegram(message):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        try:
            requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"Telegram Error: {e}")

def run_strategy():
    print(f"🚀 Starting Market Scan: {pd.Timestamp.now()}")
    
    for symbol in STOCKS:
        print(f"\n🔍 Analyzing {symbol}...")
        
        try:
            # period="2y" ensures we have enough data for a 200 EMA
            df = yf.download(symbol, period="2y", interval="1d", progress=False)
            
            if df.empty or len(df) < SLOW_MA_LEN:
                print(f"⚠️ Not enough data for {symbol}. Skipping.")
                continue

            # FIX: Use .iloc to get just the 'Close' column regardless of Multi-Index
            # This extracts the price data as a simple 1D list
            closes = df['Close']
            if isinstance(closes, pd.DataFrame):
                closes = closes.iloc[:, 0] # Take first column if it's a dataframe

            # Calculate EMAs
            df['EMA50'] = closes.ewm(span=FAST_MA_LEN, adjust=False).mean()
            df['EMA200'] = closes.ewm(span=SLOW_MA_LEN, adjust=False).mean()
            
            # Get latest two rows
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            # FIX: Force extraction of single values using .item() or float conversion
            # We select the values specifically to avoid the 'Series' error
            price = float(closes.iloc[-1])
            ema50_curr = float(curr['EMA50'])
            ema200_curr = float(curr['EMA200'])
            ema50_prev = float(prev['EMA50'])
            ema200_prev = float(prev['EMA200'])
            
            # --- Logic Check ---
            # BUY: 50 crosses ABOVE 200
            if ema50_prev <= ema200_prev and ema50_curr > ema200_curr:
                msg = f"🚀 *BUY SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nEMA50 crossed ABOVE EMA200!"
                send_telegram(msg)
                print(f"✅ SIGNAL: {msg}")

            # EXIT: 50 crosses BELOW 200
            elif ema50_prev >= ema200_prev and ema50_curr < ema200_curr:
                msg = f"📉 *EXIT SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nTrend Reversal: EMA50 below EMA200."
                send_telegram(msg)
                print(f"✅ SIGNAL: {msg}")
                
            else:
                trend = "Bullish 🟢" if ema50_curr > ema200_curr else "Bearish 🔴"
                print(f"Status: {symbol} is {trend} (No crossover today)")

        except Exception as e:
            print(f"❌ Error processing {symbol}: {str(e)}")

    print("\n✅ All stocks scanned. Process complete.")

if __name__ == "__main__":
    run_strategy()
