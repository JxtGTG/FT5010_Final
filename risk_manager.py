#!/usr/bin/env python
"""
risk_manager.py - Risk Management Module

This module provides functions for retrieving prices, account balance, computing order parameters,
placing market orders, querying open positions, calculating unrealized PnL, and closing trades.
"""

import os
from dotenv import load_dotenv
import oandapyV20
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.pricing as pricing
from oandapyV20.endpoints.accounts import AccountDetails
from oandapyV20.exceptions import V20Error
# Uncomment the following lines for email notifications if needed
# from notification import send_email_notification

load_dotenv()

access_token = os.getenv('access_token')
account_id = os.getenv('account_id')
accountID = account_id  # Ensure global variable consistency

client = oandapyV20.API(access_token=access_token, environment="practice")


def get_current_prices(instruments):
    """
    Retrieve current prices for a list of currency pairs in bulk (using bid prices).

    Parameters:
      instruments: A list of currency pairs, e.g., ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD'].

    Returns:
      A dictionary in the format {instrument: price}. Returns None if no prices are returned.
    """
    if not isinstance(instruments, list):
        instruments = [instruments]
    instrument_str = ",".join(instruments)
    params = {"instruments": instrument_str}
    try:
        request = pricing.PricingInfo(accountID=account_id, params=params)
        response = client.request(request)
        if 'prices' in response and response['prices']:
            prices = {}
            for price_info in response['prices']:
                inst = price_info.get('instrument')
                # Use bid price as the current price
                if price_info.get('bids'):
                    price = float(price_info['bids'][0]['price'])
                    prices[inst] = price
                    print(f"Current {inst} price: {price}")
            return prices
        else:
            print(f"{instrument_str} returned no price data")
            return None
    except Exception as e:
        print(f"Error retrieving prices: {e}")
        return None


def get_instrument_precision(instrument):
    """
    Return the decimal precision for the given currency pair (e.g., EUR_USD has 4 decimal places,
    USD_JPY has 2 decimal places).
    """
    instrument_precision = {
        "EUR_USD": 4,
        "AUD_USD": 4,
        "NZD_USD": 4,
        "GBP_USD": 4,
        "GBP_JPY": 2,
        "USD_JPY": 2,
        "EUR_JPY": 2
    }
    # Return 4 decimal places by default if the instrument is not found
    return instrument_precision.get(instrument, 4)


def get_current_balance():
    """
    Retrieve the current account balance.
    """
    try:
        request = AccountDetails(accountID=accountID)
        response = client.request(request)
        if response and 'account' in response:
            balance = float(response['account']['balance'])
            print(f"Current account balance: {balance}")
            return balance
    except Exception as e:
        print(f"Error getting account balance: {e}")
    return None


def get_quantities(instruments, trade_directions, stop_loss_percentage = 0.01):
    """
    Calculate the take profit price, stop loss price, and position size in bulk for each currency pair
    based on the current prices and preset percentages.

    Parameters:
      instruments: A list of currency pairs (must be 5 pairs).
      trade_directions: A dictionary where keys are instruments and values are "BUY" or "SELL".

    For each instrument, calculation is as follows:
      - If trade direction is "BUY": take profit price = current price * (1 + 0.01),
        stop loss price = current price * (1 - 0.01)
      - If trade direction is "SELL": take profit price = current price * (1 - 0.01),
        stop loss price = current price * (1 + 0.01)
      - The position size is determined by the quote currency:
          If the pair contains "USD", size = 100000; if it contains "JPY", size = 50000;
          For "SELL" trades, the position size is negative.

    Returns:
      A dictionary in the format {instrument: (stop_loss_price, take_profit_price, position_size)}.
    """
    prices = get_current_prices(instruments)
    if prices is None:
        print("Unable to obtain current prices; cannot compute order parameters")
        return None

    take_profit_percentage = 0.01  # 1%
    quantities = {}

    for inst in instruments:
        current_price = prices.get(inst)
        if current_price is None:
            print(f"{inst} has no current price; unable to compute order parameters")
            continue

        precision = get_instrument_precision(inst)
        direction = trade_directions.get(inst)
        if direction == "BUY":
            take_profit_price = round(current_price * (1 + take_profit_percentage), precision)
            stop_loss_price = round(current_price * (1 - stop_loss_percentage), precision)
        elif direction == "SELL":
            take_profit_price = round(current_price * (1 - take_profit_percentage), precision)
            stop_loss_price = round(current_price * (1 + stop_loss_percentage), precision)
        else:
            print(f"{inst} has an invalid trade direction")
            continue

        # Determine position size based on quote currency
        trade_currency = inst[4:]
        if "USD" in trade_currency:
            position_size = 100000
        elif "JPY" in trade_currency:
            position_size = 50000
        else:
            print(f"{inst} does not support the quote currency")
            continue

        if direction == "SELL":
            position_size = -position_size

        quantities[inst] = (stop_loss_price, take_profit_price, position_size)
        print(f"{inst} Calculation result: StopLoss={stop_loss_price}, TakeProfit={take_profit_price}, Quantity={position_size}")

    return quantities


def get_open_positions():
    """
    Query all currently open positions.
    """
    try:
        request = positions.OpenPositions(accountID=account_id)
        response = client.request(request)
        open_positions = response.get("positions", [])
        print(f"Number of open positions: {len(open_positions)}")
        return open_positions
    except Exception as e:
        print(f"Error querying open positions: {e}")
        return []


def calculate_total_unrealised_pnl(positions_dict):
    """
    Calculate the total unrealized profit and loss (PnL) of all positions by summing the PnL of long
    and short positions separately.
    """
    long_pnl = 0
    short_pnl = 0
    total_pnl = 0

    for position in positions_dict:
        try:
            long_unrealized_pnl = float(position['long']['unrealizedPL'])
            short_unrealized_pnl = float(position['short']['unrealizedPL'])
            long_pnl += long_unrealized_pnl
            short_pnl += short_unrealized_pnl
        except Exception as e:
            print(f"Error calculating PnL for a position: {e}")
            continue
    total_pnl = long_pnl + short_pnl
    return long_pnl, short_pnl, total_pnl


def place_market_orders(order_dict):
    """
    Place market orders in bulk with attached take profit and stop loss orders.
    
    Parameters:
      order_dict: A dictionary where keys are instruments and values are tuples of
                  (units, take_profit_price, stop_loss_price).
    """
    for inst, (units, tp, sl) in order_dict.items():
        data = {
            "order": {
                "units": str(units),
                "instrument": inst,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT",
                "takeProfitOnFill": {
                    "price": str(float(tp)),
                },
                "stopLossOnFill": {
                    "price": str(float(sl)),
                }
            }
        }
        try:
            request = orders.OrderCreate(accountID, data=data)
            response = client.request(request)
            # print(f"Order for {inst} submitted successfully: {response}")
            print(f"Order for {inst} submitted successfully!")
        except V20Error as e:
            print(f"Error submitting order for {inst}: {e}")


def close_all_trades(client, account_id):
    """
    Close all open trades.
    """
    try:
        trades_request = trades.OpenTrades(accountID=account_id)
        response = client.request(trades_request)
        trade_list = response.get('trades', [])
        if trade_list:
            for trade in trade_list:
                trade_id = trade['id']
                try:
                    data = {"units": "ALL"}
                    order_request = trades.TradeClose(accountID=account_id, tradeID=trade_id, data=data)
                    close_response = client.request(order_request)
                    # print(f"Trade {trade_id} closed successfully: {close_response}")
                    print(f"Trade {trade_id} closed successfully!")
                except V20Error as e:
                    print(f"Failed to close trade {trade_id}: {e}")
        else:
            print("There are no open trades.")
    except Exception as e:
        print(f"Error while closing all trades: {e}")


def close_position(instrument):
    """
    Close the open position for a single instrument.
    This function uses the OANDA PositionClose endpoint to close both long and short units ("ALL") for the given instrument.
    
    Parameters:
      instrument: A string, e.g. 'EUR_USD'
    
    Returns:
      The API response if successful; None otherwise.
    """
    from oandapyV20.endpoints.positions import PositionClose
    data = {"longUnits": "ALL", "shortUnits": "ALL"}
    try:
        request = PositionClose(accountID, instrument=instrument, data=data)
        response = client.request(request)
        # print(f"Position for {instrument} closed successfully: {response}")
        print(f"Position for {instrument} closed successfully")

        return response
    except Exception as e:
        print(f"Error closing position for {instrument}: {e}")
        return None
