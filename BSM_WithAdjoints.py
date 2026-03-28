import math
from scipy.stats import norm
import os
import requests

def send_telegram_dashboard(iv, delta, vega, theta):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    # Using Markdown for a bold, clean look
    message = (
        f"📊 *Option Greek Report*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔹 *IV:* `{iv:.2%}`\n"
        f"🔹 *Delta:* `{delta:.4f}`\n"
        f"🔹 *Vega:* `{vega:.2f}`\n"
        f"🔹 *Theta:* `{theta:.2f}`\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🕒 *Time:* {pd.Timestamp.now('Asia/Kolkata').strftime('%H:%M:%S')}"
    )
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})

# Call this at the end of your main block
# send_telegram_dashboard(sig, adjoints[0], adjoints[3], adjoints[5])


def BSM_withAdjoints(S0, r, y, sig, K, T):
    #Evaluation
    
    sqrtT = math.sqrt(T)
    
    df = math.exp(-r * T)
    F = S0 * math.exp((r - y) * T)
    std = sig * sqrtT
    d = math.log(F / K) / std
    d1, d2 = d + 0.5 * std, d - 0.5 * std

    nd1, nd2 = norm.cdf(d1), norm.cdf(d2)
    Call_P = df * (F * nd1 - K * nd2)
    Put_P = df * (K * (1 - nd2) - F * (1 - nd1))
    
    

    # Adjoint calculation
    
    v_ = 1.0
    
    df_ = v_ * (F * nd1 - K * nd2)
    F_ = v_ * df * nd1
    nd1_ = v_ * df * F
    
    K_ = - v_ * df * nd2
    nd2_ = - v_ * df * K
    
    d2_ = nd2_ * norm.pdf(d2)
    d1_ = nd1_ * norm.pdf(d1)
    
    d_ = d2_
    std_ = - 0.5 * d2_
    d_ += d1_
    std_ += 0.5 * d1_
    
    F_ += d_ / (F * std)
    K_ -= d_ / (K * std)
    std_ -= d_ * d / std
    
    sig_ = std_ * sqrtT
    T_ = 0.5 * std_ * sig / sqrtT
    
    S0_ = F_ * F / S0
    r_ = F_ * T * F if r == 0 else 0 
    
    y_ = - F_ * T * F if y == 0 else 0
    T_ += F_ * (r - y) * F
    

    r_ += - df_ * df * T  if r == 0 else 0
    T_ += - df_ * df * r
    
    return (Call_P,Put_P), (S0_, r_, y_, sig_, K_, T_)



def IVFromPremium(C0,S0, r, y, sig, K, T):
    V0 = sig #initial guess
    
    C=100
    while abs(C) >= 0.0001:
        OptionPrice,adjoints= BSM_withAdjoints(S0, r, y, V0, K, T)
        C1= OptionPrice[0]
        Cprime = adjoints[3]
        C = C1 - C0
        V0 = V0 - C/Cprime

    return V0 
    


if __name__ == "__main__":
    
    #Example Fwd=22816.60, Rate & Yeild=0,  Vol=0.1352, Strike=22800, DTE=6 (0.016438356)
    
    Fwd=22816.60
    Rate=0
    Yeild=0
    Strike=22800
    DTE=0.016438356 #(6 DTE)


    callPrem = 149.01
    initial_guess_vol=0.4
    
    sig= IVFromPremium(callPrem,Fwd, Rate,Yeild, initial_guess_vol, Strike, DTE)
    print("Implied Vol",sig)

    OptionPrice,adjoints= BSM_withAdjoints (Fwd, Rate,Yeild, sig, Strike, DTE)    
    

    
    print("Call Option Price:", OptionPrice[0])
    print("Put Option Price:", OptionPrice[1])

    print("S0/Delta:", adjoints[0])
    print("r/Rho:", adjoints[1])
    print("y/Dividend yeild:", adjoints[2])
    print("sig/Vega:", (adjoints[3]))
    print("K/Strike:", adjoints[4])
    print("T/Theta:", (adjoints[5]))  
