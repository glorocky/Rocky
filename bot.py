import os
import yfinance as yf
import pandas_ta_classic as ta
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# Full Weightage List (Simplified for top heavyweights to prevent API timeout)
WEIGHTS = {
    'RELIANCE.NS': 9.26, 'HDFCBANK.NS': 6.83, 'BHARTIARTL.NS': 5.70, 'SBIN.NS': 5.42, 
    'ICICIBANK.NS': 4.90, 'TCS.NS': 4.65, 'BAJFINANCE.NS': 3.11, 'LT.NS': 2.89, 
    'HINDUNILVR.NS': 2.73, 'INFY.NS': 2.56, 'MARUTI.NS': 2.32, 'AXISBANK.NS': 2.13
}

def calculate_pivot_points(df):
    """Calculates Standard Pivot, Support, and Resistance."""
    high = df['High'].iloc[-1]
    low = df['Low'].iloc[-1]
    close = df['Close'].iloc[-1]
    pivot = (high + low + close) / 3
    res1 = (2 * pivot) - low
    sup1 = (2 * pivot) - high
    return round(pivot, 2), round(res1, 2), round(sup1, 2)

def run_bot():
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    csv_file = 'market_state.csv'
    old_data = pd.read_csv(csv_file, index_col='symbol') if os.path.exists(csv_file) else pd.DataFrame()
    
    new_records = []
    report = f"🚀 *Nifty 50 weighted Update* ({datetime.now().strftime('%H:%M')})\n"
    total_score = 0
    total_weight = sum(WEIGHTS.values())

    for sym, weight in WEIGHTS.items():
        try:
            df = yf.download(sym, period='2d', interval='15m', progress=False, auto_adjust=True)
            if df.empty: continue
            
            close = df['Close']
            vol = df['Volume']
            e9 = ta.ema(close.squeeze(), length=9).iloc[-1]
            e21 = ta.ema(close.squeeze(), length=21).iloc[-1]
            pivot, res, sup = calculate_pivot_points(df)

            curr_p, curr_v = round(close.iloc[-1], 2), vol.iloc[-1]
            old_p = old_data.loc[sym, 'price'] if sym in old_data.index else curr_p
            old_v = old_data.loc[sym, 'vol'] if sym in old_data.index else curr_v

            trend = "🟢" if e9 > e21 else "🔴"
            if trend == "🟢": total_score += weight
            
            report += (f"\n*{sym.split('.')[0]}* {trend}\n"
                       f"Price: {curr_p} (Prev: {old_p})\n"
                       f"Vol: {curr_v} (Prev: {old_v})\n"
                       f"Targets: S:{sup} | R:{res}\n")

            new_records.append({'symbol': sym, 'price': curr_p, 'vol': curr_v})
        except: continue

    # Sentiment Logic
    sentiment_ratio = total_score / total_weight
    strength = round(sentiment_ratio * 10, 1)
    
    # NIFTY 50 INDEX DATA
    nifty = yf.download('^NSEI', period='2d', interval='15m', progress=False)
    n_p, n_r, n_s = calculate_pivot_points(nifty)
    
    conclusion = "🚀 BULLISH (BUY CALL)" if strength > 5.5 else "📉 BEARISH (BUY PUT)"
    
    summary = (f"\n🏁 *FINAL NIFTY 50 CONCLUSION*\n"
               f"Strength Score: {strength}/10\n"
               f"Nifty Level: {round(nifty['Close'].iloc[-1], 2)}\n"
               f"Immediate Supp: {n_s}\n"
               f"Immediate Res: {n_r}\n"
               f"Decision: *{conclusion}*")
    
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                  json={"chat_id": chat_id, "text": report + summary, "parse_mode": "Markdown"})
    
    pd.DataFrame(new_records).to_csv(csv_file, index=False)

if __name__ == "__main__":
    run_bot()
