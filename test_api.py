from api_helper import NorenApiPy
import logging

#enable dbug to see request and responses
logging.basicConfig(level=logging.DEBUG)

#start of our program
api = NorenApiPy()

#credentials
user    = 'FA79300'
pwd     = 'BTHbb@321'
factor2 = 'I765J5Q6Y6TINL6NH626E4YPA355B7DI'
vc      = 'FA79300_U'
app_key = 'f9e662cfdc675ad2cdb87e6e5c699454'
imei    = 'abc1234'

#make the api call
ret = api.login(userid=user, password=pwd, twoFA=factor2, vendor_code=vc, api_secret=app_key, imei=imei)

print(ret)
