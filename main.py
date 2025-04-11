#!/usr/bin/env python
import time
import os
import traceback
from dotenv import load_dotenv
import oandapyV20

# Import the strategy module and the risk management module
from strategy import LiveStrategy
from risk_manager import (
    get_quantities,
    place_market_orders,
    get_open_positions,
    get_current_balance,
    close_all_trades,
    close_position  # Newly added function for closing an individual instrument's position
)
# Uncomment the following import if email notifications are required
# from notification import send_email_notification

def run_strategy():
    """
    Main function to run the trading strategy.
    This function will be called when the script is executed.
    """
    # Load environment variables from .env file
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
    lookback_count = 200         # Number of historical candles to retrieve
    stma_period = 10              # Short-term moving average period
    ltma_period = 45             # Long-term moving average period
    granularity = 'H1'           # Candle granularity
    rsi_period = 10            

    # Get the initial account balance
    opening_balance = get_current_balance()

    # Default stop loss and risk-reward parameters for each instrument (these can be set individually)
    default_stoploss = 5        # Stop loss threshold
    default_risk_reward = 0.75   # Risk-reward ratio

    # Global variables indicating whether any positions are open and storing the order parameters for each instrument
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

    # Create a strategy object. It is assumed that the LiveStrategy class implements the update_signal() method to generate signals for each instrument.
    live_strategy = LiveStrategy(
        instruments=instruments,
        lookback_count=lookback_count,
        stma_period=stma_period,
        ltma_period=ltma_period,
        granularity=granularity,
        environment="practice",
        rsi_period=rsi_period
    )

    def find_quantities_and_trade(trade_directions):
        """
        Calculate order parameters and place orders based on the trading directions for each instrument,
        while recording each instrument's order parameters in the open_trade_params dictionary for later monitoring.
        
        Example format of trade_directions:
        {"EUR_USD": "BUY", "GBP_USD": "SELL", ...}
        """
        global inposition, open_trade_params
        orders_params = get_quantities(instruments, trade_directions)
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
        # Place orders in bulk
        order_dict = {inst: (quantity, takeprofit_price, stoploss_price) for inst, (stoploss_price, takeprofit_price, quantity) in orders_params.items()}
        place_market_orders(order_dict)
        print("-" * 30)
        # Save each instrument's order parameters for later monitoring
        open_trade_params = orders_params.copy()
        inposition = True
        time.sleep(3)

    # Main trading loop
    while True:
        try:
            # If no positions are open, generate signals and place orders
            if not inposition:
                trade_directions = live_strategy.update_signal()
                if not trade_directions or len(trade_directions) == 0:
                    print("No signal generated")
                else:
                    print(f"Trading opportunity detected: {trade_directions}")
                    find_quantities_and_trade(trade_directions)

            # If positions are open, monitor each instrument's position individually
            if inposition:
                positions_list = get_open_positions()  # Expected to return a list where each element contains info for an instrument
                # Iterate over each position
                for pos in positions_list:
                    # Assume the position info contains an "instrument" field and current position information (e.g., long/short parts)
                    inst = pos.get("instrument")
                    if not inst:
                        continue
                    # Here it is assumed that pos['long'] and pos['short'] both contain "unrealizedPL" and "currentPrice" (or you may obtain current price via other API calls)
                    try:
                        # This example uses pos.get("currentPrice", 0); modify as needed to fetch the actual current price
                        current_price = float(pos.get("currentPrice", 0))
                    except Exception as e:
                        print(f"Error reading current price for {inst}: {e}")
                        continue

                    # If order parameters for this instrument exist in open_trade_params, check if its individual exit condition is met
                    if inst in open_trade_params:
                        stoploss_price, takeprofit_price, _ = open_trade_params[inst]
                        # Assuming a long position: if the current price is greater than or equal to takeprofit or less than or equal to stoploss, close the position
                        if current_price >= takeprofit_price or current_price <= stoploss_price:
                            print(f"{inst}: Current price {current_price} reached target levels (TakeProfit: {takeprofit_price}, StopLoss: {stoploss_price}).")
                            close_position(inst)  # Call the function from risk_manager to close the position for this instrument only
                            # Remove the record for this instrument
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

if __name__ == "__main__":
    run_strategy()