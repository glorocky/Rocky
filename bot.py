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
    """Sends a notification to Telegram"""
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=payload)
        except Exception as e:
            print(f"Telegram Error: {e}")
    else:
        print(f"⚠️ Telegram credentials missing. Message: {message}")

def run_bot():
    print(f"🚀 Starting Market Scan: {pd.Timestamp.now()}")
    
    # 1. Initialize the results list at the START
    results = []
    
    # 2. Robust CSV Loading
    if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
        try:
            old_data = pd.read_csv(CSV_FILE, index_col='symbol')
            print("✅ Loaded existing status data.")
        except Exception as e:
            print(f"⚠️ Could not read CSV: {e}. Starting fresh.")
            old_data = pd.DataFrame()
    else:
        print("📁 No existing data found or file is empty. Creating new session.")
        old_data = pd.DataFrame()

    # 3. Process each stock
    for symbol in STOCKS:
        print(f"\n🔍 Analyzing {symbol}...")
        try:
            # Download 2 years of daily data
            df = yf.download(symbol, period="2y", interval="1d", progress=False)
            
            if df.empty or len(df) < SLOW_MA_LEN:
                print(f"⚠️ Not enough data for {symbol}. Skipping.")
                continue

            # Flatten yfinance MultiIndex headers if they exist
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Ensure we have a clean Series of Closing prices
            close_series = df['Close']
            if isinstance(close_series, pd.DataFrame):
                close_series = close_series.iloc[:, 0]

            # Calculate EMAs
            df['EMA50'] = close_series.ewm(span=FAST_MA_LEN, adjust=False).mean()
            df['EMA200'] = close_series.ewm(span=SLOW_MA_LEN, adjust=False).mean()
            
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Safe float conversion
            price = float(close_series.iloc[-1])
            ema50_curr = float(curr['EMA50'])
            ema200_curr = float(curr['EMA200'])
            ema50_prev = float(prev['EMA50'])
            ema200_prev = float(prev['EMA200'])
            
            # 4. Strategy Logic
            status = "Bearish"
            if ema50_curr > ema200_curr:
                status = "Bullish"
                # BUY: If it was Bearish/Neutral before and just crossed
                if ema50_prev <= ema200_prev:
                    send_telegram(f"🚀 *BUY SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nEMA50 crossed ABOVE EMA200!")
            else:
                # EXIT: If it was Bullish before and just crossed below
                if ema50_prev >= ema200_prev:
                    send_telegram(f"📉 *EXIT SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nTrend Reversal: EMA50 below EMA200.")

            print(f"Current Status: {status}")
            
            # Store data for CSV
            results.append({'symbol': symbol, 'status': status, 'last_price': price})

        except Exception as e:
            print(f"❌ Error processing {symbol}: {str(e)}")

    # 5. Save results to CSV
    if results:
        new_df = pd.DataFrame(results).set_index('symbol')
        new_df.to_csv(CSV_FILE)
        print(f"\n✅ Status saved to {CSV_FILE}")
    else:
        print("\n⚠️ No results were generated to save.")

if __name__ == "__main__":
    run_bot()
