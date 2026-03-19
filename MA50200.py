import pandas as pd
import yfinance as yf
import requests
import os

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CSV_FILE = "stock_status.csv"

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

def run_bot():
    print(f"🚀 Starting Market Scan: {pd.Timestamp.now()}")
    
    csv_file = "stock_status.csv"
    
    # IMPROVED: Check if file exists AND is not empty
    if os.path.exists(csv_file) and os.path.getsize(csv_file) > 0:
        try:
            old_data = pd.read_csv(csv_file, index_col='symbol')
        except pd.errors.EmptyDataError:
            print("⚠️ CSV was empty, starting fresh.")
            old_data = pd.DataFrame()
    else:
        print("📁 No existing data found, creating new session.")
        old_data = pd.DataFrame()

    # ... (rest of your analysis code)

    for symbol in STOCKS:
        print(f"\n🔍 Analyzing {symbol}...")
        try:
            # Download data
            df = yf.download(symbol, period="2y", interval="1d", progress=False)
            
            if df.empty or len(df) < SLOW_MA_LEN:
                print(f"⚠️ Not enough data for {symbol}.")
                continue

            # --- FIX: FLATTEN MULTI-INDEX DATA ---
            # This ensures we get a single column of numbers
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            close_series = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
            
            # Calculate EMAs
            df['EMA50'] = close_series.ewm(span=FAST_MA_LEN, adjust=False).mean()
            df['EMA200'] = close_series.ewm(span=SLOW_MA_LEN, adjust=False).mean()
            
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Extract scalar values safely
            price = float(close_series.iloc[-1])
            ema50_curr = float(curr['EMA50'])
            ema200_curr = float(curr['EMA200'])
            ema50_prev = float(prev['EMA50'])
            ema200_prev = float(prev['EMA200'])
            
            # Logic Check
            status = "Bearish"
            if ema50_curr > ema200_curr:
                status = "Bullish"
                if ema50_prev <= ema200_prev:
                    send_telegram(f"🚀 *BUY SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nEMA50 crossed ABOVE EMA200!")
            
            elif ema50_curr < ema200_curr:
                if ema50_prev >= ema200_prev:
                    send_telegram(f"📉 *EXIT SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nTrend Reversal: EMA50 below EMA200.")

            print(f"Current Status: {status}")
            results.append({'symbol': symbol, 'status': status, 'last_price': price})

        except Exception as e:
            print(f"❌ Error processing {symbol}: {str(e)}")

    # Save current status to CSV for next run
    if results:
        new_df = pd.DataFrame(results).set_index('symbol')
        new_df.to_csv(CSV_FILE)
        print(f"\n✅ Status saved to {CSV_FILE}")

if __name__ == "__main__":
    run_bot()

