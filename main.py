#!/usr/bin/env python
import time
import os
import traceback
from dotenv import load_dotenv
import oandapyV20

# Import the strategy module, risk manager module, and notification module (uncomment notification import if needed)
from strategy import LiveStrategy
from risk_manager import (
    get_quantities,           # This function calculates order parameters in bulk
    place_market_orders,      # Bulk order placement interface
    get_open_positions,
    get_current_balance,
    calculate_total_unrealised_pnl,
    close_all_trades
)
# from notification import send_email_notification  # Uncomment if email notifications are needed

load_dotenv()

# Load access token and account info from environment variables
access_token = os.getenv('access_token')
account_id = os.getenv('account_id')
accountID = account_id

# Initialize OANDA client (set to "practice" here; change to "live" for real trading)
client = oandapyV20.API(access_token=access_token, environment="practice")

# --------------------- Parameter Settings --------------------- #
instrument = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD']  # Currency pair list (must be 5 pairs)
lookback_count = 200         # Number of historical candlesticks to retrieve
stma_period = 9              # Short-term moving average window
ltma_period = 20             # Long-term moving average window
granularity = 'H1'           # Candlestick granularity

# Initialize trading state
inposition = False           # Flag indicating if currently in position
opening_balance = get_current_balance()
stoploss_pnl = 25            # Stop-loss threshold (example)
risk_reward = 0.75           # Risk-reward ratio, example set to 75%
target_pnl = stoploss_pnl * risk_reward

last_print_time = time.time()
time_interval = 15  # Log output interval in seconds

print("=" * 50)
print("************* STARTED LIVE TRADING **************")
print("=" * 50)
print("Starting balance     : {:.2f}".format(opening_balance))
print("Take Profit initial  : {:.2f}".format(target_pnl))
print("Stop loss initial    : {:.2f}".format(stoploss_pnl))
print("-" * 50)

# Create strategy object using the LiveStrategy class from strategy.py
live_strategy = LiveStrategy(
    instruments=instrument,
    lookback_count=lookback_count,
    stma_period=stma_period,
    ltma_period=ltma_period,
    granularity=granularity,
    environment="practice"
)

def find_quantities_and_trade(trade_directions):
    """
    Calculate order parameters and place orders based on the trading direction for each pair.
    
    Parameters:
      trade_directions: A dictionary in the format {"EUR_USD": "BUY", "GBP_USD": "SELL", ...}
    """
    global inposition
    # Call the risk manager's get_quantities function to compute order parameters in bulk, which returns a dictionary
    orders_params = get_quantities(instrument, trade_directions)
    if orders_params is None or len(orders_params) == 0:
        print("Failed to compute order parameters, abandoning trade")
        return

    print("-" * 30)
    for inst, (stoploss, takeprofit, quantity) in orders_params.items():
        print("Trade Details:")
        print(f"Instrument : {inst}")
        print(f"Volume     : {quantity}")
        print(f"StopLoss   : {stoploss}")
        print(f"TakeProfit : {takeprofit}")
    # Place orders in bulk for all instruments that have computed parameters
    order_dict = {inst: (quantity, takeprofit, stoploss) for inst, (stoploss, takeprofit, quantity) in orders_params.items()}
    place_market_orders(order_dict)
    print("-" * 30)
    inposition = True
    time.sleep(3)

# Main trading loop
while True:
    try:
        # If not currently in a position, generate signals and place orders
        if not inposition:
            trade_directions = live_strategy.update_signal()
            if not trade_directions or len(trade_directions) == 0:
                print("No signal generated")
            else:
                print(f"Trading opportunity detected: {trade_directions}")
                find_quantities_and_trade(trade_directions)
                # Uncomment send_email_notification() here if notifications are needed
        # If already in a position, monitor PnL
        if inposition:
            positions_dict = get_open_positions()
            long_pnl, short_pnl, total_pnl = calculate_total_unrealised_pnl(positions_dict)
            current_time = time.time()
            if current_time - last_print_time >= time_interval:
                print(f"Target: {target_pnl:.2f} | StopLoss: {stoploss_pnl:.2f} | PNL: {total_pnl:.2f}")
                last_print_time = current_time

            # Check if stop profit or stop loss conditions are met
            if (total_pnl > target_pnl) or (total_pnl < -stoploss_pnl):
                if total_pnl > target_pnl:
                    msg = f"Profit target reached, Target: {target_pnl:.2f} | Actual: {total_pnl:.2f}"
                else:
                    msg = f"Stop-loss triggered, Target: {target_pnl:.2f} | Actual: {total_pnl:.2f}"
                print(msg)
                close_all_trades(client, accountID)
                print("All positions closed")
                print("=" * 50)
                current_balance = get_current_balance()
                print("Current balance: {:.2f}".format(current_balance))
                # Reset state for the next trade
                inposition = False
                opening_balance = current_balance
                stoploss_pnl = 25
                risk_reward = 0.75
                target_pnl = stoploss_pnl * risk_reward
                # Uncomment send_email_notification("Closing Trades", msg) here if notifications are needed
        else:
            pass

    except Exception as e:
        print("Exception occurred in main loop:")
        traceback.print_exc()

    time.sleep(5)
