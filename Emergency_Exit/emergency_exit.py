from api_helper import NorenApiPy
import logging
import os
import datetime
import json
import time
import cProfile

api = NorenApiPy()
token_filename = datetime.datetime.now().strftime("%Y-%m-%d") + "_token.txt"
with open(token_filename, "r") as file:
    usersession = file.read().strip()

userid = "FT0XXXX"
password = 'FXXXXXXXX'

ret = api.set_session(userid= userid, password = password, usertoken= usersession) #So set_session set kar deta h ek session ko ek token se
# ret = api.get_limits()
# print(ret)
#remeber to delete eodhost from apihelper
# '''************************************************************************************************************************************************'''

def readFreezeQuantities(filename):
    freeze_quantities = {}
    full_path = "C:\\Users\\kavya\\OneDrive\\Daily API\\MyFlattrade\\pythonAPI-main\\" + filename
    try:
        with open(full_path, 'r') as file:
            for line in file:
                if '=' in line:
                    key, value = line.strip().split('=')
                    freeze_quantities[key.strip()] = int(value.strip())
        # print("Read freeze quantities:", freeze_quantities)
        return freeze_quantities
    except Exception as e:
        print("Error reading freeze quantities:", str(e))
        return {}

freeze_quantities = readFreezeQuantities('freezeQty.txt')
bankniftyFreezeQty = freeze_quantities.get("BANKNIFTY")

# Check if any of the values are None
if bankniftyFreezeQty is None:
    raise ValueError("One or more freeze quantities are not defined. Please check the freezeQty.txt file.")

# '''***********************************************************************************************************************************************'''

def punchMarketOrder(Type, ProductType, TradingSymbol, Quantity, Index):
    try:
        Exchange = "NFO"
        freezeQty = 0
        if Index == "BANKNIFTY":
            freezeQty = bankniftyFreezeQty

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

        print("Order Response:", {'stat':response['stat'],'tsym':TradingSymbol,'time':response['request_time'].split()[0]})

    except Exception as e:
        print("Error placing market order:", str(e))

# punchMarketOrder("B", "M", "NIFTY21SEP23000CE", 50, "NIFTY")

# '''***********************************************************************************************************************************************'''

def cancel_ce_sell_orders(api):
    try:
        orderBook = api.get_order_book()
        ce_sell_orders_to_cancel = []

        for order in orderBook:
            if order['status'] == 'TRIGGER_PENDING' and order['prctyp'] == "SL-LMT":
                tysm = order['tsym']
                if tysm[-6] == "C" and order['trantype'] == 'B':  # Check if it's a CE sell order
                    ce_sell_orders_to_cancel.append(order['norenordno'])

        for orderno in ce_sell_orders_to_cancel:
            order = api.cancel_order(orderno=orderno)

    except Exception as e:
        print("Error canceling CE sell orders:", str(e))

def cancel_pe_sell_orders(api):
    try:
        orderBook = api.get_order_book()
        pe_sell_orders_to_cancel = []

        for order in orderBook:
            if order['status'] == 'TRIGGER_PENDING' and order['prctyp'] == "SL-LMT":
                tysm = order['tsym']
                if tysm[-6] == "P" and order['trantype'] == 'B':  # Check if it's a PE sell order
                    pe_sell_orders_to_cancel.append(order['norenordno'])

        for orderno in pe_sell_orders_to_cancel:
            order = api.cancel_order(orderno=orderno)

    except Exception as e:
        print("Error canceling PE sell orders:", str(e))


# '''*************************************************************************************************************************************************'''
livePositions = api.get_positions()
# print(livePositions)
extracted_positions = []
if livePositions is not None:
    for position in livePositions:
        net_quantity = int(position.get('daybuyqty', 0)) + int(position.get('cfbuyqty', 0)) - int(position.get('daysellqty', 0)) - int(position.get('cfsellqty', 0))
        extracted_position = {
            'c/p': position.get('dname', ''),  # Use get with a default value
            'tsym': position['tsym'],
            'type': position['prd'],
            'net_quantity': net_quantity,
        }
        extracted_positions.append(extracted_position)

    # Now you can use extracted_positions as needed
    ce_buy_positions = [{'tsym': position['tsym'], 'type': position['type'], 'net_quantity': position['net_quantity']} #here we write type = posisiton[type] as position type means given above i.e. "M"
                        for position in extracted_positions if position['c/p'].strip().endswith('CE') and position['net_quantity'] > 0]
    pe_buy_positions = [{'tsym': position['tsym'], 'type': position['type'], 'net_quantity': position['net_quantity']}
                        for position in extracted_positions if position['c/p'].strip().endswith('PE') and position['net_quantity'] > 0]
    ce_sell_positions = [{'tsym': position['tsym'], 'type': position['type'], 'net_quantity': -position['net_quantity']}
                        for position in extracted_positions if position['c/p'].strip().endswith('CE') and position['net_quantity'] < 0]
    pe_sell_positions = [{'tsym': position['tsym'], 'type': position['type'], 'net_quantity': -position['net_quantity']}
                        for position in extracted_positions if position['c/p'].strip().endswith('PE') and position['net_quantity'] < 0]

    # print("ce_buy_positions:", ce_buy_positions)
    # print("pe_buy_positions:", pe_buy_positions)
    # print("ce_sell_positions:", ce_sell_positions)
    # print("pe_sell_positions:", pe_sell_positions)

def ceExit(Index):
    try:
        for position in ce_sell_positions:
            punchMarketOrder("B", position['type'], position['tsym'], abs(position['net_quantity']), Index)
        for position in ce_buy_positions:
            punchMarketOrder("S", position['type'], position['tsym'], abs(position['net_quantity']), Index)

        cancel_ce_sell_orders(api)

    except Exception as e:
        print("Error in ceExit:", str(e))

def peExit(Index):
    try:
        for position in pe_sell_positions:
            punchMarketOrder("B", position['type'], position['tsym'], abs(position['net_quantity']), Index)
        for position in pe_buy_positions:
            punchMarketOrder("S", position['type'], position['tsym'], abs(position['net_quantity']), Index)

        cancel_pe_sell_orders(api)

    except Exception as e:
        print("Error in peExit:", str(e))

# '''*************************************************************************************************************************************************'''
Index = "BANKNIFTY"

ceExit(Index)
peExit(Index)
