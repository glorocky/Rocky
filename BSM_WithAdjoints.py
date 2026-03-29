import time
import requests
import numpy as np
from scipy.stats import norm
from datetime import datetime, timedelta
from NorenRestApiPy.NorenApi import NorenApi
import pyotp

# 1. Initialize the Shoonya API class
class ShoonyaApiPy(NorenApi):
    def __init__(self):
        NorenApi.__init__(self, host='https://api.shoonya.com/NorenWClientTP/', 
                          websocket='wss://api.shoonya.com/NorenWSTP/')

# 2. Define 'api' in the global scope
api = ShoonyaApiPy()

def login():
    # Use your actual credentials or GitHub Secrets
    user    = 'YOUR_USER_ID'
    pwd     = 'YOUR_PASSWORD'
    vc      = 'YOUR_VENDOR_CODE'
    apikey  = 'YOUR_API_KEY'
    imei    = 'YOUR_IMEI'
    token   = 'YOUR_TOTP_TOKEN' # The 32-digit seed for TOTP
    
    totp = pyotp.TOTP(token).now()
    
    # Perform login
    ret = api.login(userid=user, password=pwd, twoFA=totp, 
                    vendor_code=vc, api_secret=apikey, imei=imei)
    
    if ret and ret.get('stat') == 'Ok':
        print("Login Successful")
    else:
        print(f"Login Failed: {ret}")
        exit(1)

def run_strategy():
    # Now 'api' is recognized here
    # 26017 is the token for INDIA VIX on NSE
    vix_data = api.get_quotes('NSE', '26017')
    if vix_data and 'lp' in vix_data:
        vix = float(vix_data['lp']) / 100 
        print(f"Current VIX: {vix}")
    # ... rest of your strategy code

# --- CONFIG & PERSISTENCE ---
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

# Symbol: [ShoonyaToken, StrikeStep, ExpiryType]
INDICES = {
    'NIFTY': ['26000', 50, 'weekly'],
    'BANKNIFTY': ['26009', 100, 'monthly'],
    'FINNIFTY': ['26037', 50, 'monthly'],
    'MIDCPNIFTY': ['26030', 25, 'monthly']
}

# Dictionary to store the last calculated straddle for decay tracking
last_straddle_prices = {}

def calculate_bs(S, K, T, r, sigma):
    if T <= 0: return 0, 0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call = (S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))
    put = (K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))
    return round(call, 2), round(put, 2)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def run_strategy():
    # api.login() logic here...
    
    # Use India VIX (Token 26017) for IV
    vix = float(api.get_quotes('NSE', '26017')['lp']) / 100 
    r = 0.07 
    
    msg_lines = [f"📅 *Premium & Decay Update*", f"Time: {datetime.now().strftime('%H:%M')}", "-"*20]

    for name, config in INDICES.items():
        try:
            spot = float(api.get_quotes('NSE', config[0])['lp'])
            atm = round(spot / config[1]) * config[1]
            T = get_days_to_expiry(name, config[2]) # Uses the Tuesday logic from previous step
            
            ce, pe = calculate_bs(spot, atm, T, r, vix)
            current_straddle = round(ce + pe, 2)
            
            # Decay Calculation
            decay_text = ""
            if name in last_straddle_prices:
                diff = round(current_straddle - last_straddle_prices[name], 2)
                symbol = "📉" if diff < 0 else "📈"
                decay_text = f" ({symbol} {diff})"
            
            last_straddle_prices[name] = current_straddle # Update for next run
            
            msg_lines.append(f"*{name}* | ATM: {atm}")
            msg_lines.append(f"CE: {ce} | PE: {pe}")
            msg_lines.append(f"💰 *Straddle: ₹{current_straddle}*{decay_text}\n")
            
        except Exception as e:
            print(f"Error processing {name}: {e}")

    send_telegram("\n".join(msg_lines))

if __name__ == "__main__":
    login()
    run_strategy()
    while True:
        now = datetime.now()
        # Market Hours logic
        if (9, 15) <= (now.hour, now.minute) <= (15, 30):
            run_strategy()
            time.sleep(1800) 
        else:
            time.sleep(60)
