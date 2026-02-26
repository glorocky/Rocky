import os
import yfinance as yf
import pandas_ta_classic as ta  # Corrected import name
import requests
import pandas as pd

def get_stock_data():
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    symbols = ['RELIANCE.NS', 'HDFCBANK.NS', 'BHARTIARTL.NS', 'SBIN.NS', 'ICICIBANK.NS', 
               'TCS.NS', 'BAJFINANCE.NS', 'LT.NS', 'HINDUNILVR.NS', 'INFY.NS']

    report = "📊 *NSE 15m Update (GitHub)*\n"
    
    for sym in symbols:
        try:
            df = yf.download(sym, period='5d', interval='15m', progress=False, auto_adjust=True)
            if df.empty: continue

            close = df['Close']

            # Indicators
            rsi = ta.rsi(close.squeeze(), length=14)
            ema9 = ta.ema(close.squeeze(), length=9)
            ema21 = ta.ema(close.squeeze(), length=21)

            # Latest values
            p = round(float(close.iloc[-1]), 2)
            r_val = round(float(rsi.iloc[-1]), 2)
            e9_val = round(float(ema9.iloc[-1]), 2)
            e21_val = round(float(ema21.iloc[-1]), 2)

            trend = "🟢" if e9_val > e21_val else "🔴"
            report += f"\n{trend} *{sym.replace('.NS','')}*: ₹{p} | RSI: {r_val}"
            
        except Exception as e:
            print(f"Error skipping {sym}: {e}")

    # Send to Telegram
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": report, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    get_stock_data()
