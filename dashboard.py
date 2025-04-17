import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import threading
import time
import plotly.graph_objects as go
from risk_manager import get_current_balance, calculate_total_unrealised_pnl, get_open_positions, close_all_trades
import oandapyV20.endpoints.instruments as instruments
import os
import oandapyV20
import numpy as np
import pandas as pd
from datetime import datetime

access_token = os.getenv('access_token')
account_id = os.getenv('account_id')
client = oandapyV20.API(access_token=access_token, environment="practice")

# Initialize the Dash app
app = dash.Dash(__name__)
app.title = "Live Trading Dashboard"

# Custom HTML template
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            :root {
                --primary: #2c3e50;
                --secondary: #3498db;
                --accent: #e74c3c;
                --success: #2ecc71;
                --warning: #f39c12;
                --danger: #e74c3c;
                --light: #ecf0f1;
                --dark: #2c3e50;
                --card-bg: #ffffff;
                --text: #333333;
            }
            
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            body {
                background-color: #f5f7fa;
                color: var(--text);
                line-height: 1.6;
                padding: 20px;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .dashboard-header {
                text-align: center;
                margin-bottom: 25px;
                border-bottom: 1px solid #ddd;
                padding-bottom: 15px;
            }
            
            h1 {
                color: var(--primary);
                font-size: 2.2rem;
                margin-bottom: 10px;
            }
            
            .strategy-description {
                background-color: var(--card-bg);
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 25px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            }
            
            .strategy-description h3 {
                color: var(--primary);
                margin-bottom: 15px;
                font-size: 1.5rem;
                border-bottom: 2px solid var(--secondary);
                padding-bottom: 8px;
                display: inline-block;
            }
            
            .strategy-description p {
                margin-bottom: 15px;
                line-height: 1.7;
            }
            
            .trading-conditions {
                margin: 20px 0;
                padding-left: 20px;
            }
            
            .condition-item {
                margin-bottom: 12px;
                padding: 10px 15px;
                border-radius: 6px;
                background-color: #f8f9fa;
                border-left: 4px solid var(--secondary);
            }
            
            .buy-condition {
                border-left-color: var(--success);
                background-color: rgba(46, 204, 113, 0.1);
            }
            
            .sell-condition {
                border-left-color: var(--danger);
                background-color: rgba(231, 76, 60, 0.1);
            }
            
            .hold-condition {
                border-left-color: var(--warning);
                background-color: rgba(243, 156, 18, 0.1);
            }
            
            .condition-label {
                font-weight: bold;
                margin-right: 5px;
            }
            
            .buy-label {
                color: var(--success);
            }
            
            .sell-label {
                color: var(--danger);
            }
            
            .hold-label {
                color: var(--warning);
            }
            
            .metrics-container {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 25px;
            }
            
            .metric-card {
                background-color: var(--card-bg);
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
                transition: transform 0.3s ease;
            }
            
            .metric-card:hover {
                transform: translateY(-5px);
            }
            
            .metric-card h4 {
                color: var(--primary);
                font-size: 1.1rem;
                margin-bottom: 15px;
            }
            
            
            .additional-metrics-container {
                background-color: var(--card-bg);
                border-radius: 8px;
                padding: 20px;
                text-align: center;
            }
            
            .additional-metrics-container:hover {
                transform: translateY(-5px);
            }
            
            .metric-card h4 {
                color: var(--primary);
                font-size: 1.1rem;
                margin-bottom: 15px;
            }
            
            .metric-value {
                font-size: 1.8rem;
                font-weight: bold;
            }
            
            .positive {
                color: var(--success);
            }
            
            .negative {
                color: var(--danger);
            }
            
            .neutral {
                color: var(--primary);
            }
            
            .kill-switch-container {
                margin-top: 20px;
                text-align: center;
                margin-bottom: 25px;
            }
            
            .kill-switch {
                background-color: var(--danger);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 5px;
                font-size: 1rem;
                font-weight: bold;
                cursor: pointer;
                transition: background-color 0.3s ease;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            
            .kill-switch:hover {
                background-color: #c0392b;
            }
            
            .kill-switch.triggered {
                background-color: #95a5a6;
                cursor: not-allowed;
            }
            
            .time-range-selector {
                width: 100%;
                max-width: 500px;
                margin: 0 auto 25px auto;
            }
            
            .time-range-selector h4 {
                color: var(--primary);
                margin-bottom: 10px;
                text-align: center;
            }
            
            .dropdown {
                width: 100%;
                border-radius: 5px;
                border: 1px solid #ddd;
                background-color: white;
                font-size: 1rem;
                outline: none;
            }
            
            .chart-container {
                background-color: var(--card-bg);
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 25px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            }
            
            @media (max-width: 768px) {
                .metrics-container {
                    grid-template-columns: 1fr;
                }
            }
            
            .status-indicator {
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                margin-right: 5px;
                background-color: var(--success);
            }
            
            .status-inactive {
                background-color: var(--danger);
            }
            
            .dashboard-footer {
                text-align: center;
                font-size: 0.9rem;
                color: #95a5a6;
                margin-top: 20px;
            }
            
            /* Positions table styles */
            .positions-container {
                grid-column: 1 / -1;
                background-color: var(--card-bg);
                border-radius: 8px;
                padding: 20px;
                margin-top: 20px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            }
            
            .positions-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }
            
            .positions-table th, .positions-table td {
                padding: 15px 20px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            
            .positions-table th {
                background-color: #f8f9fa;
                color: var(--primary);
                font-weight: 600;
                font-size: 1.1rem;
            }
            
            .positions-table td {
                font-size: 1.1rem;
            }
            
            .positions-table tr:hover {
                background-color: #f8f9fa;
            }
            
            .no-positions {
                text-align: center;
                padding: 30px;
                color: #95a5a6;
                font-style: italic;
                font-size: 1.2rem;
            }
            
            .positions-heading {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }
            
            .positions-heading h3 {
                color: var(--primary);
                margin: 0;
                font-size: 1.5rem;
            }
            
            .position-badge {
                display: inline-block;
                padding: 6px 12px;
                border-radius: 15px;
                font-size: 1rem;
                font-weight: bold;
            }
            
            .profit {
                background-color: rgba(46, 204, 113, 0.2);
                color: var(--success);
            }
            
            .loss {
                background-color: rgba(231, 76, 60, 0.2);
                color: var(--danger);
            }
            
            .pnl-cell {
                font-weight: bold;
                font-size: 1.1rem;
            }
            
            .realized-pnl-cell {
                font-weight: bold;
                font-size: 1.1rem;
            }
            
            .instrument-cell {
                font-weight: 500;
                font-size: 1.2rem;
            }
            
            .position-size {
                font-weight: 500;
            }
            
            .position-long {
                color: var(--success);
                font-weight: bold;
            }
            
            .position-short {
                color: var(--danger);
                font-weight: bold;
            }
            
            .entry-price {
                font-weight: 500;
            }
            
            .margin-used {
                font-size: 0.95rem;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="container">
            {%app_entry%}
        </div>
        <footer class="dashboard-footer">
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Global variables
running_strategy = {
    "description": """This code implements a live trading strategy for forex markets using technical analysis. It retrieves historical price data from OANDA and generates trading signals ("BUY", "SELL", or "HOLD") for multiple currency pairs based on the following conditions:""",
    "buy_condition": """BUY: Short-term SMA > Long-term SMA, RSI < 70, and Current Price > Short-term EMA.""",
    "sell_condition": """SELL: Short-term SMA < Long-term SMA or RSI > 70. Take-profit levels are set at 1%, and stop-loss levels at 0.5%.""",
    "hold_condition": """HOLD: When neither BUY nor SELL conditions are met.""",
    "conclusion": """The strategy continuously updates signals in real-time for the specified currency pairs.""",
    "instrument": "EUR_USD",
    "stma_period": 9,
    "ltma_period": 20,
    "lookback_count": 200,
    "benchmark": "EUR/USD",
    "risk_free_rate": 0.02  # Annual risk-free rate (2%)
}
current_pnl = 0
current_balance = get_current_balance()
initial_balance = current_balance  # Record the initial balance
open_positions = []
kill_switch_triggered = False # Initialize the kill_switch_triggered flag

eurusd_prices = []
eurusd_returns = []
eurusd_timestamps = []
initial_eurusd_price = None
current_eurusd_return = 0
# Function to calculate Risk of Ruin based on maximum drawdown
def calculate_max_drawdown(returns):
    if not returns:
        return 0.0
    peak = returns[0]
    max_drawdown = 0.0
    for r in returns:
        if r > peak:
            peak = r
        drawdown = peak - r
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    return max_drawdown

def calculate_ratios(returns, timestamps, risk_free_rate=0.02, max_drawdown=0.0):
    if len(returns) < 2 or len(timestamps) < 2:
        return {
            'Sharpe Ratio': 0.0,
            'Daily Return': 0.0,
            'Daily Volatility': 0.0,
            'Calmar Ratio': 0.0,
            'Sortino Ratio': 0.0
        }

    total_seconds = (timestamps.iloc[-1] - timestamps.iloc[0]).total_seconds()
    total_days = total_seconds / (24 * 60 * 60)
    if total_days == 0:
        raise ValueError("Time span too short for daily calculation.")

    n = len(returns)
    rf_daily = (1 + risk_free_rate) ** (1 / 260) - 1  # 转为每日无风险利率
    excess_returns = returns - rf_daily

    # Sharpe Ratio (daily)
    std = returns.std()
    if std == 0:
        sharpe_ratio = 0.0
    else:
        sharpe_ratio = excess_returns.mean() / std

    # Daily Return
    cumulative_return = (returns + 1).prod() - 1
    daily_return = (1 + cumulative_return) ** (1 / total_days) - 1

    # Daily Volatility
    daily_volatility = std

    # Calmar Ratio (daily return / max drawdown)
    calmar_ratio = daily_return / max_drawdown if max_drawdown != 0 else np.nan

    # Sortino Ratio (daily)
    downside_returns = excess_returns[excess_returns < 0]
    downside_vol = downside_returns.std()
    sortino_ratio = (daily_return - rf_daily) / downside_vol if downside_vol > 0 else np.nan

    # return {
    #     'Sharpe Ratio': sharpe_ratio,
    #     'Daily Return': daily_return,
    #     'Daily Volatility': daily_volatility,
    #     'Calmar Ratio': calmar_ratio,
    #     'Sortino Ratio': sortino_ratio,
    # }
    result = {}
    for key, value in {
        'Sharpe Ratio': sharpe_ratio,
        'Daily Return': daily_return,
        'Daily Volatility': daily_volatility,
        'Calmar Ratio': calmar_ratio,
        'Sortino Ratio': sortino_ratio,
    }.items():
        if isinstance(value, (int, float)) and not np.isnan(value):
            if abs(value) > 1e6 or (abs(value) < 1e-4 and value != 0):
                value = "{:.4e}".format(value)
            else:
                value = float(value) 
        result[key] = value

    return result
    
# Lists to store returns over time
strategy_returns = []  # List to store strategy returns (percentage values)
equity_series = [initial_balance]
timestamps = []  # List to store corresponding timestamps
benchmark_return = (running_strategy["risk_free_rate"] / 365) * 100  # Daily risk-free rate converted to percentage

# Update data function
def update_data():
    global current_balance, current_pnl, open_positions, strategy_returns, timestamps, equity_series
    global eurusd_prices, eurusd_returns, eurusd_timestamps, initial_eurusd_price, current_eurusd_return
    
    while True:
        try:
            # Update balance and calculate return
            current_balance = get_current_balance()
            open_positions_dict = get_open_positions()
            _, _, current_pnl = calculate_total_unrealised_pnl(open_positions_dict)

            # Update global variables
            open_positions = open_positions_dict
            
            # Modified return calculation: (unrealized PnL + current balance)/initial_balance
            strategy_return = ((current_balance + current_pnl - initial_balance) / initial_balance) * 100
            cur_equity = current_balance + current_pnl
            # Append data for plotting and risk calculation
            strategy_returns.append(strategy_return)
            equity_series.append(cur_equity)
            timestamps.append(time.time())  # Use Unix timestamp for accurate time filtering
            
            # Update EUR/USD data
            params = {
                "count": 1,
                "granularity": "S5"  # 5-second granularity
            }
            
            r = instruments.InstrumentsCandles(instrument="EUR_USD", params=params)
            client.request(r)
            candles = r.response.get('candles', [])
            
            if candles and len(candles) > 0:
                # get the current price
                current_price = float(candles[0]['mid']['c'])
                current_timestamp = time.time()
                
                # Check if initial price is set
                if initial_eurusd_price is None:
                    initial_eurusd_price = current_price
                
                # Calculate the return
                eurusd_return = ((current_price - initial_eurusd_price) / initial_eurusd_price) * 100
                current_eurusd_return = eurusd_return
                
                # Append data for EUR/USD
                eurusd_prices.append(current_price)
                eurusd_returns.append(eurusd_return)
                eurusd_timestamps.append(current_timestamp)
            
        except Exception as e:
            print(f"Error updating data: {e}")
        time.sleep(5)

# Start the data update thread
thread = threading.Thread(target=update_data, daemon=True)
thread.start()

# Function to generate the positions table with carefully selected information
def generate_positions_table(positions):
    if not positions:
        return html.Div(className="no-positions", children=["No open positions at the moment."])
    
    # Create table header with the most valuable information
    header = html.Tr([
        html.Th("Instrument"),
        html.Th("Position Size"),
        html.Th("Entry Price"),
        html.Th("Unrealized P/L"),
        html.Th("Total P/L")
    ])
    
    # Create table rows for each position
    rows = []
    for position in positions:
        # Extract instrument
        instrument = position.get("instrument", "Unknown")
        
        # Get position details - focusing on long position since that's what's active in your example
        long_units = "0"
        avg_price = "0.00000"
        
        if "long" in position and position["long"] and "units" in position["long"]:
            long_dict = position["long"]
            try:
                long_units = int(float(long_dict.get("units", "0")))
                avg_price = float(long_dict.get("averagePrice", "0"))
            except (ValueError, TypeError):
                long_units = 0
                avg_price = 0
        
        short_units = "0"
        if "short" in position and position["short"] and "units" in position["short"]:
            short_dict = position["short"]
            try:
                short_units = int(float(short_dict.get("units", "0")))
            except (ValueError, TypeError):
                short_units = 0
        
        # Determine position type
        position_type = ""
        position_units = 0
        position_class = ""
        
        if long_units and int(long_units) > 0:
            position_type = "LONG"
            position_units = long_units
            position_class = "position-long"
        elif short_units and int(short_units) < 0:
            position_type = "SHORT"
            position_units = short_units
            position_class = "position-short"
        
        # Get unrealized and total P/L
        try:
            unrealized_pnl = float(position.get("unrealizedPL", "0"))
        except (ValueError, TypeError):
            unrealized_pnl = 0
            
        try:
            total_pl = float(position.get("pl", "0"))
        except (ValueError, TypeError):
            total_pl = 0
            
        # Format the margin used if available
        try:
            margin_used = float(position.get("marginUsed", "0"))
            margin_text = f"Margin: ${margin_used:.2f}"
        except (ValueError, TypeError):
            margin_text = ""
        
        # Style for P/L
        unrealized_pnl_class = "pnl-cell profit" if unrealized_pnl >= 0 else "pnl-cell loss"
        total_pnl_class = "realized-pnl-cell profit" if total_pl >= 0 else "realized-pnl-cell loss"
        
        # Create row with the most important information
        row = html.Tr([
            html.Td([
                html.Div(str(instrument).replace("_", "/"), className="instrument-cell"),
                html.Div(margin_text, className="margin-used") if margin_text else ""
            ]),
            html.Td(html.Span(f"{abs(position_units):,}", className=position_class)),
            html.Td(f"{avg_price:.5f}", className="entry-price"),
            html.Td(html.Span(f"${unrealized_pnl:.2f}", className=unrealized_pnl_class)),
            html.Td(html.Span(f"${total_pl:.2f}", className=total_pnl_class))
        ])
        
        rows.append(row)
    
    return html.Table(
        className="positions-table",
        children=[
            html.Thead(header),
            html.Tbody(rows)
        ]
    )

# Dash layout with updated classes
app.layout = html.Div(
    className="container",
    children=[
        dcc.ConfirmDialog(
            id='close-trades-dialog',
            message='All trades have been closed successfully!',
            displayed=False,
        ),
        
        html.Div(
            className="dashboard-header",
            children=[
                html.H1("Trading Strategy Dashboard"),
                html.Div(
                    className="status-container",
                    children=[
                        html.Span(className="status-indicator", id="status-indicator"),
                        html.Span("Strategy Active", id="status-text")
                    ]
                )
            ]
        ),
        
        # Strategy Description with separated conditions
        html.Div(
            className="strategy-description",
            children=[
                html.H3("Strategy Description"),
                html.P(running_strategy["description"]),
                html.Div(
                    className="trading-conditions",
                    children=[
                        html.Div(
                            className="condition-item buy-condition",
                            children=[
                                html.Span("BUY: ", className="condition-label buy-label"),
                                running_strategy["buy_condition"]
                            ]
                        ),
                        html.Div(
                            className="condition-item sell-condition",
                            children=[
                                html.Span("SELL: ", className="condition-label sell-label"),    
                                running_strategy["sell_condition"]
                            ]
                        ),
                        html.Div(
                            className="condition-item hold-condition",
                            children=[
                                html.Span("HOLD: ", className="condition-label hold-label"),
                                running_strategy["hold_condition"],
                            ]
                        ),
                    ]
                ),
                html.P(running_strategy["conclusion"]),
            ]
        ),

        # Strategy Parameters - Metrics Cards
        html.Div(
            className="metrics-container",
            children=[
                html.Div(
                    className="metric-card",
                    children=[
                        html.H4("Current Equity"),
                        html.P(id="equity-display", className="metric-value neutral"),
                    ]
                ),
                html.Div(
                    className="metric-card",
                    children=[
                        html.H4("Current PNL"),
                        html.P(id="pnl-display", className="metric-value"),
                    ]
                ),
                html.Div(
                    className="metric-card",
                    children=[
                        html.H4("Benchmark Return(EUR/USD)"),
                        html.P(id="eurusd-return-display", className="metric-value neutral"),
                    ]
                ),
                html.Div(
                    className="metric-card",
                    children=[
                        html.H4("Max Drawdown"),
                        html.P(id="risk-display", className="metric-value neutral"),
                    ]
                ),
            ]
        ),
        
        # Additional Metrics Container
        html.Div(id="additional-metrics-container"),

        # Open Positions Details (spans all columns)
        html.Div(
            className="positions-container",
            children=[
                html.Div(
                    className="positions-heading",
                    children=[
                        html.H3("Open Positions Details"),
                        html.Div(id="positions-summary")
                    ]
                ),
                html.Div(id="positions-details")
            ]
        ),

        # Kill Switch Button
        html.Div(
            className="kill-switch-container",
            children=[
                html.Button("Kill Switch: Close All Trades", id="kill-switch", className="kill-switch", n_clicks=0),
            ]
        ),

        # Dropdown for selecting time range
        html.Div(
            className="time-range-selector",
            children=[
                html.H4("Select Time Range for Returns Analysis"),
                dcc.Dropdown(
                    id="time-range-dropdown",
                    className="dropdown",
                    options=[
                        {"label": "Last 1 Minute", "value": 60},
                        {"label": "Last 2 Minutes", "value": 120},
                        {"label": "Last 5 Minutes", "value": 300},
                        {"label": "Last 15 Minutes", "value": 900},
                        {"label": "Last 1 Hour", "value": 3600},
                    ],
                    value=120,  # Default to 2 minutes
                    clearable=False,
                ),
            ]
        ),

        # Performance Chart
        html.Div(
            className="chart-container",
            children=[
                dcc.Graph(id="performance-chart"),
            ]
        ),

        # Interval component to trigger updates
        dcc.Interval(id="interval", interval=5000, n_intervals=0),
    ]
)

# Callback: update strategy data with PNL color and Risk of Ruin based on strategy_returns
@app.callback(
    [Output("equity-display", "children"),
     Output("pnl-display", "children"),
     Output("pnl-display", "className"),
     Output("eurusd-return-display", "children"),  
     Output("eurusd-return-display", "className"),  
     Output("risk-display", "children"),
     Output("risk-display", "className"),
     Output("positions-details", "children"),
     Output("positions-summary", "children"),
     Output("additional-metrics-container", "children")],  

    [Input("interval", "n_intervals")]
)
def update_strategy_data(n):
    global current_balance, current_pnl, open_positions, strategy_returns, current_eurusd_return
    
    equity = f"${current_balance:.2f}"
    pnl = f"${current_pnl:.2f}"
    
    # Determine PNL class based on current PNL
    if current_pnl > 0:
        pnl_class = "metric-value positive"
    elif current_pnl < 0:
        pnl_class = "metric-value negative"
    else:
        pnl_class = "metric-value neutral"
    
    # CSS class for EUR/USD return
    eurusd_return_str = f"{current_eurusd_return:.2f}%"
    if current_eurusd_return > 0:
        eurusd_return_class = "metric-value positive"
    elif current_eurusd_return < 0:
        eurusd_return_class = "metric-value negative"
    else:
        eurusd_return_class = "metric-value neutral"
    
    # Calculate Risk of Ruin based on strategy returns
    risk = calculate_max_drawdown(strategy_returns)
    risk_str = f"{risk:.2f}%"
    if risk < 10:
        risk_class = "metric-value positive"
    elif risk < 30:
        risk_class = "metric-value neutral"
    else:
        risk_class = "metric-value negative"
    
    # Calculate risk metrics
    try:
        all_ratios = {}
        if len(strategy_returns) > 1 and len(timestamps) > 1:
            all_ratios = calculate_ratios(
                pd.Series(equity_series).pct_change(), 
                pd.Series([datetime.fromtimestamp(ts) for ts in timestamps]), 
                risk_free_rate=running_strategy["risk_free_rate"],
                max_drawdown=risk/100
            )
        else:
            all_ratios = {
                'Sharpe Ratio': 0.0,
                'Daily Return': 0.0,
                'Daily Volatility': 0.0,
                'Calmar Ratio': 0.0,
                'Sortino Ratio': 0.0
            }
            
        sharpe_ratio = all_ratios['Sharpe Ratio']
        daily_return = all_ratios['Daily Return']
        daily_volatility = all_ratios['Daily Volatility']
        calmar_ratio = all_ratios['Calmar Ratio']
        sortino_ratio = all_ratios['Sortino Ratio']
        
        # Create additional metrics cards
        additional_metrics = html.Div(
            style={
                "display": "grid", 
                "gridTemplateColumns": "repeat(5, 1fr)", 
                "gap": "20px",
                "marginBottom": "25px"
            },
            children=[
                html.Div(
                    className="metric-card",
                    children=[
                        html.H4("Daily Sharpe Ratio"),
                        html.P(f"{sharpe_ratio:.2f}", className="metric-value " + ("positive" if sharpe_ratio > 1 else "neutral" if sharpe_ratio > 0 else "negative"))
                    ]
                ),
                html.Div(
                    className="metric-card",
                    children=[
                        html.H4("Daily Return"),
                        html.P(f"{daily_return*100:.2f}%", className="metric-value " + ("positive" if daily_return > 0 else "negative"))
                    ]
                ),
                html.Div(
                    className="metric-card",
                    children=[
                        html.H4("Daily Volatility"),
                        html.P(f"{daily_volatility*100:.2f}%", className="metric-value " + ("positive" if daily_volatility < 0.1 else "neutral" if daily_volatility < 0.2 else "negative"))
                    ]
                ),
                html.Div(
                    className="metric-card",
                    children=[
                        html.H4("Daily Calmar Ratio"),
                        html.P(f"{calmar_ratio:.2f}" if not np.isnan(calmar_ratio) else "N/A", className="metric-value " + ("positive" if calmar_ratio > 2 else "neutral" if calmar_ratio > 1 else "negative"))
                    ]
                ),
                html.Div(
                    className="metric-card",
                    children=[
                        html.H4("Daily Sortino Ratio"),
                        html.P(f"{sortino_ratio:.2f}" if not np.isnan(sortino_ratio) else "N/A", className="metric-value " + ("positive" if sortino_ratio > 1 else "neutral" if sortino_ratio > 0 else "negative"))
                    ]
                )
            ]
        )
    except Exception as e:
        print(f"Error calculating ratios: {e}")
        additional_metrics = html.Div()  # Empty div if error occurs

    # Generate positions table with the most valuable information
    positions_table = generate_positions_table(open_positions)
    
    # Create positions summary badges with proper type conversion
    total_profit = sum(float(pos.get("unrealizedPL", 0)) 
                      for pos in open_positions 
                      if isinstance(pos.get("unrealizedPL", 0), (int, float, str)) 
                      and float(pos.get("unrealizedPL", 0)) > 0)
    
    total_loss = sum(float(pos.get("unrealizedPL", 0)) 
                    for pos in open_positions 
                    if isinstance(pos.get("unrealizedPL", 0), (int, float, str)) 
                    and float(pos.get("unrealizedPL", 0)) < 0)
    
    positions_count = len(open_positions)
    if positions_count == 0:
        positions_summary = html.Span("No open positions")
    else:
        positions_summary = html.Div([
            html.Span(f"{positions_count} Position{'s' if positions_count > 1 else ''} | ", style={"marginRight": "5px"}),
            html.Span(f"Profit: ${total_profit:.2f}", className="position-badge profit", style={"marginRight": "10px"}),
            html.Span(f"Loss: ${total_loss:.2f}", className="position-badge loss")
        ])
    
    return equity, pnl, pnl_class, eurusd_return_str, eurusd_return_class, risk_str, risk_class, positions_table, positions_summary, additional_metrics
# Callback: kill switch to close all trades and update status
@app.callback(
    [Output("kill-switch", "children"),
     Output("kill-switch", "className"),
     Output("status-indicator", "className"),
     Output("status-text", "children")],
    [Input("kill-switch", "n_clicks")]
)
def kill_switch(n_clicks):
    # global kill_switch_triggered
    global open_positions
    # global open_positions   
    if n_clicks > 0 and n_clicks is not None:
        try: 
            # kill_switch_triggered = True
            close_all_trades(client, account_id)  # Close all trades
            open_positions = []  # Reset open positions to empty
            return ("Kill Switch: Close All Trades", 
                    "kill-switch", 
                    "status-indicator", 
                    "Strategy Active")
        except Exception as e:
            print(f"Error closing trades: {e}")
    
    return ("Kill Switch: Close All Trades", 
            "kill-switch", 
            "status-indicator", 
            "Strategy Active")

@app.callback(
    Output("close-trades-dialog", "displayed"),
    [Input("kill-switch", "n_clicks")]
)
def display_confirmation(n_clicks):
    # Display confirmation dialog if the kill switch is clicked
    if n_clicks is not None and n_clicks > 0:
        changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
        if 'kill-switch' in changed_id:
            return True
    return False

# Callback: update performance chart based on time range
@app.callback(
    Output("performance-chart", "figure"),
    [Input("time-range-dropdown", "value"),
     Input("interval", "n_intervals")]
)
def update_performance_chart(time_range, n):
    global strategy_returns, timestamps, eurusd_returns, eurusd_timestamps

    # Filter data based on selected time range
    current_time = time.time()
    
    # filter strategy returns
    filtered_indices = [i for i, t in enumerate(timestamps) if current_time - t <= time_range]
    filtered_timestamps = [timestamps[i] for i in filtered_indices]
    filtered_returns = [strategy_returns[i] for i in filtered_indices]

    # filter eurusd returns
    filtered_eurusd_indices = [i for i, t in enumerate(eurusd_timestamps) if current_time - t <= time_range]
    # filtered_eurusd_timestamps = [eurusd_timestamps[i] for i in filtered_eurusd_indices]
    filtered_eurusd_returns = [eurusd_returns[i] for i in filtered_eurusd_indices]

    # Convert timestamps to readable format
    readable_timestamps = [time.strftime("%H:%M:%S", time.localtime(t)) for t in filtered_timestamps]
    # readable_eurusd_timestamps = [time.strftime("%H:%M:%S", time.localtime(t)) for t in filtered_eurusd_timestamps]

    # Create the figure with improved styling
    fig = go.Figure()

    # Add strategy returns as a line
    fig.add_trace(go.Scatter(
        x=readable_timestamps,
        y=filtered_returns,
        mode='lines+markers',
        name="Strategy Returns",
        line=dict(color='#3498db', width=3),
        marker=dict(size=8)
    ))

    # Add EUR/USD returns as a line (instead of benchmark)
    fig.add_trace(go.Scatter(
        x=readable_timestamps,
        y=filtered_eurusd_returns,
        mode='lines',
        name="EUR/USD Returns",
        line=dict(color='#e74c3c', width=2)
    ))

    # Update layout with better styling
    fig.update_layout(
        title="Strategy Returns vs EUR/USD",
        xaxis_title="Time",
        yaxis_title="Returns (%)",
        plot_bgcolor='rgba(240, 242, 245, 0.8)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showline=True, showgrid=True, gridcolor='rgba(200, 200, 200, 0.2)'),
        yaxis=dict(showline=True, showgrid=True, gridcolor='rgba(200, 200, 200, 0.2)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified",
    )

    return fig


# Run the Dash app
if __name__ == "__main__":
    app.run_server(debug=True)