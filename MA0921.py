import pandas as pd
import yfinance as yf
import requests
import os

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CSV_FILE = "stock_status.csv"

FAST_MA_LEN = 9
SLOW_MA_LEN = 21
STOCKS = ["BHARTIARTL.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS"]

def send_telegram(message):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        try:
            requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"Telegram Error: {e}")

def run_bot():
    print(f"🚀 Starting Market Scan: {pd.Timestamp.now()}")
    
    # 1. Initialize the results list at the START
    results = []
    
    # 2. Safely check for existing CSV
    if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
        try:
            old_data = pd.read_csv(CSV_FILE, index_col='symbol')
        except Exception:
            print("⚠️ Could not read CSV, starting fresh.")
            old_data = pd.DataFrame()
    else:
        print("📁 No existing data found, creating new session.")
        old_data = pd.DataFrame()

    for symbol in STOCKS:
        print(f"\n🔍 Analyzing {symbol}...")
        try:
            df = yf.download(symbol, period="2y", interval="1d", progress=False)
            
            if df.empty or len(df) < SLOW_MA_LEN:
                print(f"⚠️ Not enough data for {symbol}.")
                continue

            # Flatten yfinance data headers
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Extract closing prices safely
            close_series = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
            
            # Calculate Indicators
            df['EMA9'] = close_series.ewm(span=FAST_MA_LEN, adjust=False).mean()
            df['EMA21'] = close_series.ewm(span=SLOW_MA_LEN, adjust=False).mean()
            
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            price = float(close_series.iloc[-1])
            ema9_curr = float(curr['EMA9'])
            ema21_curr = float(curr['EMA21'])
            ema9_prev = float(prev['EMA9'])
            ema21_prev = float(prev['EMA21'])
            
            # Logic Check
            status = "Bearish"
            if ema9_curr > ema21_curr:
                status = "Bullish"
                # Check for Crossover (Buy)
                if ema9_prev <= ema21_prev:
                    send_telegram(f"🚀 *BUY SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nEMA9 crossed ABOVE EMA21!")
            else:
                # Check for Crossunder (Exit)
                if ema9_prev >= ema21_prev:
                    send_telegram(f"📉 *EXIT SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nTrend Reversal: EMA9 below EMA21.")

            print(f"Current Status: {status}")
            
            # Append to the results list
            results.append({'symbol': symbol, 'status': status, 'last_price': price})

        except Exception as e:
            print(f"❌ Error processing {symbol}: {str(e)}")

    # 3. Save results to CSV (Now results is guaranteed to exist)
    if results:
        new_df = pd.DataFrame(results).set_index('symbol')
        new_df.to_csv(CSV_FILE)
        print(f"\n✅ Status saved to {CSV_FILE}")
    else:
        print("\n⚠️ No results to save.")

if __name__ == "__main__":
    run_bot()

