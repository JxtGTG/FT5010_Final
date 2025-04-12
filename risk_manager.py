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


def get_quantities(instruments, trade_directions, rsi_dict, rsi_weight_param=1):
    """
    Calculate the take profit price, stop loss price, and dynamic position size for each currency pair
    in bulk based on current prices, available account funds, preset percentages, and each pair's RSI data.

    Parameters:
      instruments: A list of currency pairs (must be 5 pairs).
      trade_directions: A dictionary where keys are currency pairs and values are "BUY" or "SELL", e.g.:
          {
              "EUR_USD": "BUY",
              "GBP_USD": "SELL",
              "USD_JPY": "BUY",
              "AUD_USD": "BUY",
              "USD_CAD": "SELL"
          }
      rsi_dict: A dictionary where keys are currency pairs and values are the corresponding RSI values, e.g.:
          {
              "EUR_USD": 65,
              "GBP_USD": 75,
              "USD_JPY": 60,
              "AUD_USD": 68,
              "USD_CAD": 72
          }
      rsi_weight_param: RSI weighting parameter (default is 1) used to adjust the weight distribution.

    Calculation logic:
      - First, obtain current prices for all currency pairs and the available account funds.
      - For each currency pair with a BUY or SELL signal, calculate the weight using:
            weight = max(70 - current RSI, 0) ** rsi_weight_param.
      - For BUY (or SELL) signals, allocate funds proportionally based on the weight:
            allocated funds = available cash * (weight of pair / sum of weights for all BUY or SELL pairs).
      - If the trade direction is "BUY":
            - Take profit price = current price * (1 + 0.01)
            - Stop loss price = current price * (1 - 0.01)
            - Position size = allocated funds / current price (rounded to an integer)
      - If the trade direction is "SELL":
            - Take profit price = current price * (1 - 0.01)
            - Stop loss price = current price * (1 + 0.01)
            - Position size = - (allocated funds / current price) (rounded to an integer, negative indicates a sell)

    Returns:
      A dictionary in the format {currency_pair: (stop_loss_price, take_profit_price, position_size)}.
      If the parameters for a given currency pair cannot be computed, that pair is skipped.
    """
    prices = get_current_prices(instruments)
    if prices is None:
        print("Unable to obtain current prices; cannot compute order parameters")
        return None

    available_cash = get_current_balance()
    if available_cash is None:
        print("Unable to obtain account balance; cannot compute order parameters")
        return None

    take_profit_percentage = 0.01  # 1%
    stop_loss_percentage = 0.01      # 1%
    quantities = {}

    # Calculate weights separately for BUY and SELL signals.
    buy_weights = {}
    sell_weights = {}
    for inst in instruments:
        direction = trade_directions.get(inst)
        if inst not in rsi_dict:
            print(f"{inst} is missing RSI data")
            continue
        current_rsi = rsi_dict[inst]
        weight = max(70 - current_rsi, 0) ** rsi_weight_param
        if direction == "BUY":
            buy_weights[inst] = weight
        elif direction == "SELL":
            sell_weights[inst] = weight
        else:
            print(f"{inst} has an invalid trade direction")
    total_buy_weight = sum(buy_weights.values()) if buy_weights else 0
    total_sell_weight = sum(sell_weights.values()) if sell_weights else 0

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
            if total_buy_weight > 0:
                allocation = available_cash * (buy_weights.get(inst, 0) / total_buy_weight)
            else:
                allocation = 0
            quantity = round(allocation / current_price, 0)
        elif direction == "SELL":
            take_profit_price = round(current_price * (1 - take_profit_percentage), precision)
            stop_loss_price = round(current_price * (1 + stop_loss_percentage), precision)
            if total_sell_weight > 0:
                allocation = available_cash * (sell_weights.get(inst, 0) / total_sell_weight)
            else:
                allocation = 0
            quantity = -round(allocation / current_price, 0)
        else:
            print(f"{inst} has an invalid trade direction")
            continue

        quantities[inst] = (stop_loss_price, take_profit_price, quantity)
        print(f"{inst} Calculation result: StopLoss={stop_loss_price}, TakeProfit={take_profit_price}, Quantity={quantity}")

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
