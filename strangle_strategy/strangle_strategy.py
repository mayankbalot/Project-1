# If we keep this whole process in crosshair login file then wo har baar new request code generate karego and then new token, but we want one token per day,
# so now first we generate new token and save it in token file via crosshairlogin and then via test_api we can login multiple times with single token in a day

from api_helper import NorenApiPy
import logging
import os
import datetime

#enable dbug to see request and responses
# logging.basicConfig(level=logging.DEBUG)

#start of our program
api = NorenApiPy()

#set token and user id
token_filename = datetime.datetime.now().strftime("%Y-%m-%d") + "_token.txt"
with open(token_filename, "r") as file:
    usersession = file.read().strip()

userid = "FT0XYZZZ"
password = 'XYZZZZZ'

ret = api.set_session(userid= userid, password = password, usertoken= usersession) #So set_session set kar deta h ek session ko ek token se
ret = api.get_limits()
print(ret)

#remeber to delete eodhost from apihelper
'''**************************************************************************************************************************************************************'''
# FOR FINDING SPOT ATM 
def FindAtmStrike(LTP,Index):
    
    if Index == "NIFTY" or Index == "FINNIFTY":
        strikeDiff = 50
    elif Index == "BANKNIFTY" or Index == "SENSEX" :
        strikeDiff = 100 
    
    elif Index == "MIDCPNIFTY" :
        strikeDiff = 25
    
    
    if LTP%strikeDiff >= strikeDiff/2 :
        AtmStrike =  LTP - LTP % strikeDiff +strikeDiff
    else :
        AtmStrike = LTP - LTP%strikeDiff
    
    return int(AtmStrike)

niftyLTP = api.get_quotes("NSE", "26000").get('lp')
bankNiftyLTP = api.get_quotes("NSE", "26009").get('lp')
finNiftyLTP = api.get_quotes("NSE", "26037").get('lp')

'''****************************************************************************************************'''
# FOR FINDING OPTION STRIKE = NIFTY24AUG23C19300

def defineStrikes(Index, Expiry, LTP, callDiff, putDiff):
    Year = str(datetime.datetime.now().year % 100) #here we did the mode of year as we only need its last 2 digits like 23 not whole 2023
    ce = (Index + Expiry + Year + "C" + str(FindAtmStrike((float(LTP) + callDiff), Index)))
    pe = (Index + Expiry + Year + "P" + str(FindAtmStrike((float(LTP) - putDiff), Index)))
    return {"CE": ce, "PE": pe}


'''****************************************************************************************************'''

def readFreezeQuantities(filename):
    freeze_quantities = {}
    full_path = "C:\\Users\\kavya\\OneDrive\\API\\Flattrade\\pythonAPI-main\\freezeQty.txt"
    with open(full_path, 'r') as file:
        for line in file:
            key, value = line.strip().split('=')
            freeze_quantities[key.strip()] = int(value.strip())
    print("Read freeze quantities:", freeze_quantities)
    return freeze_quantities

freeze_quantities = readFreezeQuantities('freezeQty.txt')

niftyFreezeQty = freeze_quantities.get("NIFTY")
bankniftyFreezeQty = freeze_quantities.get("BANKNIFTY")
finniftyFreezeQty = freeze_quantities.get("FINNIFTY")

# Check if any of the values are None
if niftyFreezeQty is None or bankniftyFreezeQty is None or finniftyFreezeQty is None:
    raise ValueError("One or more freeze quantities are not defined. Please check the freezeQty.txt file.")

def punchMarketOrder(Type, ProductType, TradingSymbol, Quantity , Index):
    if Index == "SENSEX":
        Exchange ="BFO"
    else: 
        Exchange= "NFO"
   
    freezeQty = 0
    if Index == "NIFTY":
        freezeQty = niftyFreezeQty
    elif Index == "BANKNIFTY":
        freezeQty = bankniftyFreezeQty
    elif Index == "FINNIFTY":
        freezeQty = finniftyFreezeQty

    while Quantity >= freezeQty:  
        response = api.place_order(buy_or_sell=Type, product_type=ProductType,
                                    exchange=Exchange, tradingsymbol=TradingSymbol, 
                                    quantity=freezeQty, discloseqty=0, price_type='MKT', price=0,
                                    retention='DAY', remarks='selling ce')
        Quantity = Quantity - freezeQty

    if Quantity < freezeQty:
        response = api.place_order(buy_or_sell=Type, product_type=ProductType,
                                    exchange=Exchange, tradingsymbol=TradingSymbol, 
                                    quantity=Quantity, discloseqty=0, price_type='MKT', price=0,
                                    retention='DAY', remarks='selling ce')

    print("Order Response:", response)


'''****************************************************************************************************'''

def cpStranglePunch(ProductType, Index,QuantityHedge, Quantity, TradingSymbol):
    punchMarketOrder("B", ProductType, TradingSymbol.get('hedgeCE'), QuantityHedge , Index)  #here TradingSymbol.get('hedgeCE') kaam karega when ClosestPremiumStrangle ek dict me ho
    punchMarketOrder("B", ProductType, TradingSymbol.get('hedgePE'), QuantityHedge , Index)
    punchMarketOrder("S", ProductType, TradingSymbol.get('CE'), Quantity , Index)
    punchMarketOrder("S", ProductType, TradingSymbol.get('PE'), Quantity , Index)
print("closestStranglePunch function done")
'''****************************************************************************************************'''

def FindClosestPremium(premiums, premium):
    min = premiums[0]
    diff = abs(premium - premiums[0].get('lp')) #.get('lp') cause we want 
    for i in premiums:
        if (diff > abs(premium-i.get('lp'))):
            diff = abs(premium-i.get('lp'))
            min = i
        elif (diff == abs(premium-i.get('lp')) and i.get('lp') > min.get('lp')): #this gives just above if diff is same
            diff == abs(premium-i.get('lp'))
            min = i
    return min

'''****************************************************************************************************'''

def getOptionChain(LTP, Index):
    i =0
    optionChain = []
    AtmStrike = FindAtmStrike(float(LTP), Index)
    while i <= 20:
        if Index == "NIFTY" or "FINNIFTY":
            strikes = defineStrikes(Index, Expiry, LTP, i*50, i*50)
        elif Index == "BANKNIFTY":
            strikes = defineStrikes(Index, Expiry, LTP, i*100, i*100)
        elif Index == "MIDCPNIFTY":
            strikes = defineStrikes(Index, Expiry, LTP, i*25, i*25)

        optionChain.append({'tsym':strikes.get('CE') , 'optt':'CE' , 'strike' : i, 'lp':api.get_quotes('NFO',strikes.get('CE') ).get('lp')}  )
        optionChain.append({'tsym':strikes.get('PE') , 'optt':'PE' ,'strike' : i, 'lp':api.get_quotes('NFO',strikes.get('PE') ).get('lp')}  )
        i =  i+1
    return optionChain

'''****************************************************************************************************'''

def ClosestPremiumStrangle(optionChain, premium , hedgePremium):       
    premiumsCE = []
    premiumsPE = []
   
    for option in optionChain:
        if(option.get('optt')== 'CE'):
            premiumsCE.append( {"lp": float(option['lp']) , "tsym":option['tsym']})
        else :
            premiumsPE.append( {"lp": float(option['lp']) , "tsym":option['tsym']})
        print(option)
   

    return {
        "CE":FindClosestPremium(premiumsCE, premium).get('tsym'),
        "PE":FindClosestPremium(premiumsPE ,  premium).get('tsym'),
        'hedgeCE':FindClosestPremium(premiumsCE ,  hedgePremium).get('tsym'),
        'hedgePE':FindClosestPremium(premiumsPE ,  hedgePremium).get('tsym')
    }


ProductType = "M"
Index = "NIFTY"
Expiry = "31AUG"
LTP = niftyLTP
QuantityHedge = 150
Quantity = 150
optionChain = getOptionChain(LTP, Index)
premium = 30
hedgePremium = 3

# print(ClosestPremiumStrangle(optionChain, premium , hedgePremium))

cpStranglePunch(ProductType, Index, QuantityHedge , Quantity, ClosestPremiumStrangle(optionChain, premium, hedgePremium))
