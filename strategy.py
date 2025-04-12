#!/usr/bin/env python
"""
strategy.py - Live Trading Strategy Module

This module retrieves recent historical data from OANDA H1 and generates live trading signals using the same strategy as in backtesting.
It supports multiple currency pairs. The signal generation logic for each pair is as follows:
  - Calculate short-term SMA, long-term SMA, short-term EMA, and RSI.
  - "BUY" condition: short SMA > long SMA, RSI < 70, and current price > short EMA.
  - "SELL" condition: short SMA < long SMA or RSI > 70.
  - Otherwise, return "HOLD".

Additionally, this version returns the latest computed RSI along with the signal.
"""

import numpy as np
import os
import time
import pandas as pd
from datetime import datetime
from oandapyV20 import API
from oandapyV20.endpoints.instruments import InstrumentsCandles
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class LiveStrategy:
    def __init__(self, instruments, lookback_count=200, stma_period=9, ltma_period=20, rsi_period=30, 
                 granularity='H1', environment="practice"):
        """
        Initialize live trading strategy parameters.
        
        Parameters:
          instruments: A list of currency pairs, e.g., ['EUR_USD', 'GBP_USD', ...]. 
                       If a single string is provided, it will be automatically converted to a list.
          lookback_count: Number of historical candlesticks to retrieve.
          stma_period: Period for calculating short-term SMA.
          ltma_period: Period for calculating long-term SMA.
          rsi_period: Period for calculating RSI.
          granularity: The candlestick granularity (default is 'H1').
          environment: The trading environment, "practice" or "live".
        """
        if isinstance(instruments, str):
            instruments = [instruments]
        self.instruments = instruments
        self.lookback_count = lookback_count
        self.stma_period = stma_period
        self.ltma_period = ltma_period
        self.rsi_period = rsi_period
        self.granularity = granularity
        self.environment = environment
        
        self.access_token = os.getenv('access_token')
        if not self.access_token:
            raise ValueError("access_token is not set. Please configure it in your environment variables.")
        self.account_id = os.getenv('account_id')
        if not self.account_id:
            raise ValueError("account_id is not set. Please configure it in your environment variables.")
        
        self.client = API(access_token=self.access_token, environment=self.environment)
    
    def fetch_candlestick_data(self, instrument):
        """
        Retrieve the most recent 'lookback_count' candlestick data for the specified currency pair from OANDA.
        Uses the 'M' (mid) price data.
        
        Parameters:
          instrument: A single currency pair, e.g., 'EUR_USD'
          
        Returns:
          A list of closing prices, or None if data retrieval fails.
        """
        params = {
            'count': self.lookback_count,
            'granularity': self.granularity,
            'price': 'M'
        }
        candles_request = InstrumentsCandles(instrument=instrument, params=params)
        try:
            response = self.client.request(candles_request)
        except Exception as e:
            print(f"Error retrieving data for {instrument}: {e}")
            return None
        
        candles = response.get('candles', [])
        if not candles:
            print(f"No data returned for {instrument}")
            return None
        
        # Process only completed candles
        close_prices = [float(candle['mid']['c']) for candle in candles if candle.get('complete', False)]
        if len(close_prices) < max(self.ltma_period, self.rsi_period):
            print(f"Insufficient data for {instrument}; at least {max(self.ltma_period, self.rsi_period)} complete candles are required.")
            return None
        
        return close_prices

    def update_signal(self):
        """
        For each currency pair, generate a live trading signal based on the latest historical data, along with the latest RSI.
        
        For each instrument:
          - Calculate short-term SMA, long-term SMA, short-term EMA, and RSI.
          - "BUY": if short SMA > long SMA, RSI < 70, and current price > short EMA.
          - "SELL": if short SMA < long SMA or RSI > 70.
          - Otherwise, "HOLD".
        
        Returns:
          A dictionary in the format {instrument: {"signal": signal, "rsi": latest_rsi}}.
        """
        results = {}
        for inst in self.instruments:
            close_prices = self.fetch_candlestick_data(inst)
            if close_prices is None:
                results[inst] = {"signal": None, "rsi": None}
                continue
            
            price_series = pd.Series(close_prices)
            
            # Calculate short-term SMA and long-term SMA
            short_sma = price_series.rolling(window=self.stma_period).mean().iloc[-1]
            long_sma = price_series.rolling(window=self.ltma_period).mean().iloc[-1]
            
            # Calculate short-term EMA
            short_ema = price_series.ewm(span=self.stma_period, adjust=False).mean().iloc[-1]
            
            # Calculate RSI
            delta = price_series.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(window=self.rsi_period, min_periods=self.rsi_period).mean().iloc[-1]
            avg_loss = loss.rolling(window=self.rsi_period, min_periods=self.rsi_period).mean().iloc[-1]
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            current_price = price_series.iloc[-1]
            
            # Generate signal based on strategy
            if (short_sma > long_sma) and (rsi < 70) and (current_price > short_ema):
                signal = "BUY"
            elif (short_sma < long_sma) or (rsi > 70):
                signal = "SELL"
            else:
                signal = "HOLD"
            
            print(f"[{datetime.now()}] {inst} - short_SMA: {short_sma:.5f}, long_SMA: {long_sma:.5f}, "
                  f"short_EMA: {short_ema:.5f}, RSI: {rsi:.2f}, Price: {current_price:.5f}, Signal: {signal}")
            results[inst] = {"signal": signal, "rsi": rsi}
        
        return results

# Test section
if __name__ == "__main__":
    # Define multiple currency pairs
    instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD']
    strategy = LiveStrategy(instruments=instruments, lookback_count=200, stma_period=10, ltma_period=45, rsi_period=10)
    
    while True:
        output = strategy.update_signal()
        # Print the current signals and RSI values
        print(f"Current output: {output}")
        time.sleep(60)  # Update signals every 60 seconds
