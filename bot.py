import os
import yfinance as yf
import pandas_ta as ta
import requests
import pandas as pd

def get_stock_data():
    # Fetching secrets from GitHub Settings
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    TOP_10 = [
        {'sym': 'RELIANCE'}, {'sym': 'HDFCBANK'}, {'sym': 'BHARTIARTL'}, 
        {'sym': 'SBIN'}, {'sym': 'ICICIBANK'}, {'sym': 'TCS'},
        {'sym': 'BAJFINANCE'}, {'sym': 'LT'}, {'sym': 'HINDUNILVR'}, {'sym': 'INFY'}
    ]

    report_lines = ["📊 *NSE 15m Update*\n"]
    
    for stock in TOP_10:
        symbol = f"{stock['sym']}.NS"
        try:
            df = yf.download(symbol, period='5d', interval='15m', progress=False, auto_adjust=True)
            if df.empty: continue

            # Handle column selection
            close_prices = df['Close'].iloc[:, 0] if len(df['Close'].shape) > 1 else df['Close']
            volume_data = df['Volume'].iloc[:, 0] if len(df['Volume'].shape) > 1 else df['Volume']

            # Indicators
            rsi = ta.rsi(close_prices, length=14)
            e9 = ta.ema(close_prices, length=9)
            e21 = ta.ema(close_prices, length=21)

            # Get Last Values
            p = round(float(close_prices.iloc[-1]), 2)
            r_val = round(float(rsi.iloc[-1]), 2)
            ema9_val = round(float(e9.iloc[-1]), 2)
            ema21_val = round(float(e21.iloc[-1]), 2)

            trend = "🟢" if ema9_val > ema21_val else "🔴"
            report_lines.append(f"{trend} *{stock['sym']}*: ₹{p} | RSI: {r_val}\n   E9: {ema9_val} | E21: {ema21_val}")
            
        except Exception as e:
            print(f"Error {symbol}: {e}")

    # Send to Telegram
    full_message = "\n".join(report_lines)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": full_message, "parse_mode": "Markdown"})

if __name__ == "__main__":
    get_stock_data()
