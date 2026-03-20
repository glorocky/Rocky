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
    
    results = []
    summary_lines = ["📊 *Daily Market Summary* 📊\n"] # New: List to hold summary text
    
    # 1. Load existing CSV data
    csv_file = "stock_status.csv"
    if os.path.exists(csv_file) and os.path.getsize(csv_file) > 0:
        try:
            old_data = pd.read_csv(csv_file, index_col='symbol')
        except Exception:
            old_data = pd.DataFrame()
    else:
        old_data = pd.DataFrame()

    for symbol in STOCKS:
        print(f"\n🔍 Analyzing {symbol}...")
        try:
            df = yf.download(symbol, period="2y", interval="1d", progress=False)
            
            if df.empty or len(df) < SLOW_MA_LEN:
                continue

            # Flatten yf headers
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            close_series = df['Close']
            if isinstance(close_series, pd.DataFrame):
                close_series = close_series.iloc[:, 0]

            # Calculate EMAs
            df['EMA50'] = close_series.ewm(span=FAST_MA_LEN, adjust=False).mean()
            df['EMA200'] = close_series.ewm(span=SLOW_MA_LEN, adjust=False).mean()
            
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            price = float(close_series.iloc[-1])
            ema50_curr = float(curr['EMA50'])
            ema200_curr = float(curr['EMA200'])
            ema50_prev = float(prev['EMA50'])
            ema200_prev = float(prev['EMA200'])
            
            # Logic Check
            status = "🔴 Bearish"
            if ema50_curr > ema200_curr:
                status = "🟢 Bullish"
                # ALERT: New Buy Crossover
                if not old_data.empty and symbol in old_data.index:
                    if old_data.loc[symbol, 'status'] != "🟢 Bullish":
                        send_telegram(f"🚀 *NEW BUY SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nTrend flipped to Bullish!")
            else:
                # ALERT: New Exit Crossover
                if not old_data.empty and symbol in old_data.index:
                    if old_data.loc[symbol, 'status'] != "🔴 Bearish":
                        send_telegram(f"📉 *NEW EXIT SIGNAL: {symbol}*\nPrice: ₹{price:.2f}\nTrend flipped to Bearish!")

            # Add this stock to the Daily Summary
            summary_lines.append(f"{symbol}: {status} (₹{price:.2f})")
            
            # Store data for next run
            results.append({'symbol': symbol, 'status': status, 'last_price': price})

        except Exception as e:
            print(f"❌ Error processing {symbol}: {str(e)}")

    # 2. SEND THE DAILY SUMMARY
    if summary_lines:
        full_summary = "\n".join(summary_lines)
        send_telegram(full_summary)
        print("✅ Daily Summary sent to Telegram.")

    # 3. Save to CSV
    if results:
        new_df = pd.DataFrame(results).set_index('symbol')
        new_df.to_csv(csv_file)

if __name__ == "__main__":
    # 1. TEST MESSAGE (This MUST arrive if your secrets are correct)
    print("Testing Telegram Connection...")
    send_telegram("🔔 *TEST ALERT:* If you see this, your GitHub Secrets are working!")
    
    # 2. Run the actual bot logic
    run_bot()
