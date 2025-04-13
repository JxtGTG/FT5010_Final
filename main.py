#!/usr/bin/env python
import time
import os
import traceback
from dotenv import load_dotenv
import oandapyV20

# Import the strategy module and the risk management module
from strategy import LiveStrategy
from risk_manager import (
    get_quantities,           # Revised function with RSI weighting to calculate order parameters
    place_market_orders,      # Bulk order placement interface
    get_open_positions,
    get_current_balance,
    close_all_trades,
    close_position            # Function for closing an individual instrument’s position
)
# Uncomment the following import if email notifications are required
# from notification import send_email_notification

load_dotenv()

# Load account credentials and information
access_token = os.getenv('access_token')
account_id = os.getenv('account_id')
accountID = account_id

# Initialize the OANDA API client (using practice mode)
client = oandapyV20.API(access_token=access_token, environment="practice")

# --------------------- Settings --------------------- #
# Define the instruments (5 currency pairs)
instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD']
lookback_count = 200          # Number of historical candles to retrieve
stma_period = 30              # Short-term moving average period
ltma_period = 40              # Long-term moving average period
granularity = 'S5'            # Candle granularity
rsi_period = 10               # RSI period
rsi_weight_param = 1         # Weighting parameter for RSI in order quantity calculation

# Get the initial account balance
opening_balance = get_current_balance()


# Global variables indicating whether any positions are open and storing each instrument's order parameters.
# Format: { "EUR_USD": (stop_loss_price, take_profit_price, quantity), ... }
inposition = False
open_trade_params = {}

last_print_time = time.time()
time_interval = 15  # Log output interval (in seconds)

print("=" * 50)
print("************* STARTED LIVE TRADING **************")
print("=" * 50)
print("Starting balance     : {:.2f}".format(opening_balance))
print("-" * 50)

# Create a strategy object. It is assumed that the LiveStrategy class implements the update_signal() method
# which returns a dictionary of the form {instrument: {"signal": signal, "rsi": rsi}}.
live_strategy = LiveStrategy(
    instruments=instruments,
    lookback_count=lookback_count,
    stma_period=stma_period,
    ltma_period=ltma_period,
    granularity=granularity,
    environment="practice",
    rsi_period=rsi_period
)

def find_quantities_and_trade(signal_results):
    """
    Calculate order parameters using RSI weights and place orders.
    This function extracts the trade directions and RSI values from the signal results and passes them into
    the get_quantities function to compute the order parameters, then places orders in bulk.

    Parameters:
      signal_results: A dictionary of the format {instrument: {"signal": signal, "rsi": rsi}}.
    """
    global inposition, open_trade_params
    trade_directions = {}
    rsi_dict = {}
    # Extract trade directions and RSI data from signal_results
    for inst, data in signal_results.items():
        if data is None:
            continue
        trade_directions[inst] = data.get("signal")
        rsi_dict[inst] = data.get("rsi")
    
    orders_params = get_quantities(instruments, trade_directions, rsi_dict, rsi_weight_param=rsi_weight_param)
    if orders_params is None or len(orders_params) == 0:
        print("Failed to compute order parameters, abandoning trade")
        return

    print("-" * 30)
    for inst, (stoploss_price, takeprofit_price, quantity) in orders_params.items():
        print("Trade Details:")
        print(f"Instrument : {inst}")
        print(f"Volume     : {quantity}")
        print(f"StopLoss   : {stoploss_price}")
        print(f"TakeProfit : {takeprofit_price}")
    # Place orders in bulk for all instruments with computed order parameters
    order_dict = {inst: (quantity, takeprofit_price, stoploss_price)
                  for inst, (stoploss_price, takeprofit_price, quantity) in orders_params.items()}
    place_market_orders(order_dict)
    print("-" * 30)
    # Save the order parameters for later monitoring
    open_trade_params = orders_params.copy()
    inposition = True
    time.sleep(3)

# Main trading loop
while True:
    try:
        # If no positions are open, generate signals and place orders
        if not inposition:
            signal_results = live_strategy.update_signal()
            if not signal_results or len(signal_results) == 0:
                print("No signal generated")
            else:
                print(f"Signal results: {signal_results}")
                find_quantities_and_trade(signal_results)
                
        # If positions are open, monitor each instrument's position individually
        if inposition:
            positions_list = get_open_positions()  # Returns a list containing position information for each instrument
            for pos in positions_list:
                # Assume position info contains an "instrument" field and current position info
                inst = pos.get("instrument")
                if not inst:
                    continue
                try:
                    # This example uses pos.get("currentPrice", 0); modify as needed to fetch the actual current price
                    current_price = float(pos.get("currentPrice", 0))
                except Exception as e:
                    print(f"Error reading current price for {inst}: {e}")
                    continue

                # If order parameters exist for this instrument, check if the individual exit condition is met
                if inst in open_trade_params:
                    stoploss_price, takeprofit_price, _ = open_trade_params[inst]
                    # For a long position: if current price >= take profit or current price <= stop loss, then exit
                    if current_price >= takeprofit_price or current_price <= stoploss_price:
                        print(f"{inst}: Current price {current_price} reached target levels (TP: {takeprofit_price}, SL: {stoploss_price}).")
                        close_position(inst)  # Close the position for this instrument only
                        # Remove the record from open_trade_params
                        open_trade_params.pop(inst, None)
                else:
                    continue

            # Check whether all positions have been closed
            positions_list = get_open_positions()
            if not positions_list or len(positions_list) == 0:
                inposition = False
                current_balance = get_current_balance()
                print("=" * 50)
                print("All positions closed")
                print("Current balance: {:.2f}".format(current_balance))
                # Update account balance and reset state
                opening_balance = current_balance
                open_trade_params = {}
        else:
            pass

    except Exception as e:
        print("Exception occurred in main loop:")
        traceback.print_exc()

    time.sleep(5)
