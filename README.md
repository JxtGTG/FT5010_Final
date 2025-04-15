# 🚀 Forex Trading Bot

A forex trading bot with real-time dashboard visualization for monitoring and analyzing the performance of trading strategies across multiple currency pairs.


## 📋 Project Overview

This project implements an automated trading system for forex markets using technical analysis indicators. The bot analyzes historical price data from OANDA and generates trading signals for multiple currency pairs based on moving averages and RSI indicators.

## ✨ Key Features

- 📊 **Multi-Currency Trading**: Supports trading on multiple forex pairs simultaneously
- 📈 **Technical Analysis Strategy**: Uses SMA, EMA, and RSI indicators to generate signals
- 💰 **Dynamic Position Sizing**: Allocates funds based on RSI weighting algorithm
- 🛡️ **Risk Management**: Implements take-profit and stop-loss levels
- 📱 **Live Dashboard**: Real-time monitoring of trades, PnL, and performance metrics
- 🔄 **Multiprocessing Architecture**: Separates trading logic from dashboard for optimal performance

## 🧩 Strategy Logic

The trading strategy generates signals based on the following conditions:

- **BUY** ✅: Short-term SMA > Long-term SMA, RSI < 70, and Current Price > Short-term EMA
- **SELL** ❌: Short-term SMA < Long-term SMA or RSI > 70. Take-profit levels are set at 1%, and stop-loss levels at 0.5%.
- **HOLD** ⏸️: When neither BUY nor SELL conditions are met


## 📁 Project Structure

- `strategy.py`: Implements the live trading strategy using technical indicators
- `risk_manager.py`: Handles position sizing, order execution, and risk management
- `main.py`: Main trading loop that manages signals and trade execution
- `dashboard.py`: Interactive web dashboard for monitoring performance
- `multiprocess.py`: Orchestrates the main trading process and dashboard

## 📊 Dashboard Features

- Real-time account equity and PnL tracking
- Performance comparison against EUR/USD benchmark
- Risk metrics including max drawdown
- Advanced performance metrics (Sharpe, Sortino, Calmar ratios)
- Open positions table with detailed trade information
- Emergency kill switch to close all trades
- Time-series chart for performance visualization

## 🔧 Requirements

- Python 3.7+
- OANDA API access token
- Trading account ID
- Required packages

## ⚙️ Environment Variables

Create a `.env` file with the following variables:
```
access_token=your_oanda_access_token
account_id=your_oanda_account_id
```

## 🚀 Getting Started

1. Clone the repository
2. Install required packages
3. Set up your `.env` file with OANDA credentials
4. Run the application using multiprocess:

```bash
python multiprocess.py
```

> ⚠️ **IMPORTANT**: Always run the application via `multiprocess.py` to ensure both the trading bot and dashboard start correctly.

## 🖥️ Dashboard Access

Once running, access the dashboard at:
```
http://127.0.0.1:8050/
```
## 💡 Dashboard Layout 

![](https://raw.githubusercontent.com/Ukrys/DFintech_Courses_images/master/202504141957372.png)

## 🔍 Advanced Configuration

You can customize trading parameters in `main.py`:

- Currency pairs
- Lookback period
- Moving average periods
- RSI settings
- Risk parameters

## ⚠️ Risk Warning

This trading bot is provided for educational purposes only. Trading forex carries substantial risk of loss and is not suitable for all investors. Always test thoroughly in a demo environment before using with real money.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.


Happy Trading! 📈