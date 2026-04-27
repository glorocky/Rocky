import time
import requests
import numpy as np
from scipy.stats import norm
from datetime import datetime, timedelta
from NorenRestApiPy.NorenApi import NorenApi
import pyotp
import base64
try:
    # Replace with your actual string to test
    test_secret = "YOUR_SECRET_HERE".strip().replace(" ", "")
    base64.b32decode(test_secret, casefold=True)
    print("Token is valid Base32!")
except Exception as e:
    print(f"Token is INVALID: {e}")

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


