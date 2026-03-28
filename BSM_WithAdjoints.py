import calendar
import time
import requests
import numpy as np
from scipy.stats import norm
from NorenRestApiPy.NorenApi import NorenApi
from datetime import datetime, timedelta

# --- SETTINGS ---
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

# {Symbol: [ShoonyaToken, StrikeStep, ExpiryType]}
INDICES = {
    'NIFTY': ['26000', 50, 'weekly'],
    'BANKNIFTY': ['26009', 100, 'monthly'],
    'FINNIFTY': ['26037', 50, 'monthly'],
    'MIDCPNIFTY': ['26030', 25, 'monthly']
}

def get_last_tuesday(dt):
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    last_date = datetime(dt.year, dt.month, last_day)
    offset = (last_date.weekday() - 1) % 7 # 1 is Tuesday
    return last_date - timedelta(days=offset)

def get_days_to_expiry(name, expiry_type):
    now = datetime.now()
    if expiry_type == 'weekly':
        days_ahead = (1 - now.weekday()) % 7 # Target Tuesday
        if days_ahead == 0 and now.hour >= 15: days_ahead = 7
        target_date = now + timedelta(days=days_ahead)
    else:
        target_date = get_last_tuesday(now)
        if now.date() > target_date.date() or (now.date() == target_date.date() and now.hour >= 15):
            next_month = now.replace(day=28) + timedelta(days=5)
            target_date = get_last_tuesday(next_month)
    
    expiry_time = target_date.replace(hour=15, minute=30, second=0)
    seconds_diff = (expiry_time - now).total_seconds()
    return max(seconds_diff / (365 * 24 * 3600), 0.0001)

def calculate_bs(S, K, T, r, sigma):
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call = (S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))
    put = (K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))
    return round(call, 2), round(put, 2)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def run_strategy():
    # api = ShoonyaApi() 
    # api.login(...)
    
    # India VIX as proxy for IV
    vix = float(api.get_quotes('NSE', '26017')['lp']) / 100 
    r = 0.07 
    
    msg = [f"📅 *Market Update: {datetime.now().strftime('%H:%M')}*", "-"*20]

    for name, config in INDICES.items():
        try:
            spot = float(api.get_quotes('NSE', config[0])['lp'])
            atm = round(spot / config[1]) * config[1]
            T = get_days_to_expiry(name, config[2])
            
            ce, pe = calculate_bs(spot, atm, T, r, vix)
            straddle = round(ce + pe, 2)
            
            msg.append(f"*{name}* (ATM: {atm})")
            msg.append(f"CE: ₹{ce} | PE: ₹{pe}")
            msg.append(f"💰 *Straddle Price: ₹{straddle}*\n")
        except:
            continue

    send_telegram("\n".join(msg))

if __name__ == "__main__":
    while True:
        now = datetime.now()
        # Market Hours: 9:15 to 15:30
        if (now.hour == 9 and now.minute >= 15) or (10 <= now.hour < 15) or (now.hour == 15 and now.minute <= 30):
            run_strategy()
            time.sleep(1800) # 30 mins
        else:
            time.sleep(60)

