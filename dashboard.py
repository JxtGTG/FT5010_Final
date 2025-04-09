import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import threading
import time
import plotly.graph_objects as go
from risk_manager import get_current_balance, calculate_total_unrealised_pnl, get_open_positions, close_all_trades
import os
import oandapyV20

access_token = os.getenv('access_token')
account_id = os.getenv('account_id')
client = oandapyV20.API(access_token=access_token, environment="practice")

# Initialize the Dash app
app = dash.Dash(__name__)
app.title = "Live Trading Dashboard"

# 自定义 HTML 模板，包含 CSS
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
    "sell_condition": """SELL: Short-term SMA < Long-term SMA or RSI > 70.""",
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
kill_switch_triggered = False  # Track if the Kill Switch has been activated

# Lists to store returns over time
strategy_returns = []  # List to store strategy returns
timestamps = []  # List to store corresponding timestamps
benchmark_return = (running_strategy["risk_free_rate"] / 365) * 100  # Daily risk-free rate converted to percentage

# Update data function
def update_data():
    global current_balance, current_pnl, open_positions, strategy_returns, timestamps, kill_switch_triggered
    while True:
        if kill_switch_triggered:  # Stop updating data if Kill Switch is triggered
            print("Kill Switch triggered. Stopping strategy updates.")
            break
        try:
            # Update balance and calculate return
            current_balance = get_current_balance()
            open_positions_dict = get_open_positions()
            _, _, current_pnl = calculate_total_unrealised_pnl(open_positions_dict)

            # Update global variables
            open_positions = open_positions_dict
            strategy_return = ((current_balance - initial_balance) / initial_balance) * 100

            # Append data for plotting
            strategy_returns.append(strategy_return)
            timestamps.append(time.time())  # Use Unix timestamp for accurate time filtering
        except Exception as e:
            print(f"Error updating data: {e}")
        time.sleep(5)

# Start the data update thread
thread = threading.Thread(target=update_data, daemon=True)
thread.start()

# Dash layout with updated classes
app.layout = html.Div(
    className="container",
    children=[
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

        # Strategy Description
        # html.Div(
        #     className="strategy-description",
        #     children=[
        #         html.H3("Strategy Description"),
        #         html.Div(running_strategy["description"]),
        #     ]
        # ),
        
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
                                "Short-term SMA > Long-term SMA, RSI < 70, and Current Price > Short-term EMA."
                            ]
                        ),
                        html.Div(
                            className="condition-item sell-condition",
                            children=[
                                html.Span("SELL: ", className="condition-label sell-label"),
                                "Short-term SMA < Long-term SMA or RSI > 70."
                            ]
                        ),
                        html.Div(
                            className="condition-item hold-condition",
                            children=[
                                html.Span("HOLD: ", className="condition-label hold-label"),
                                "When neither BUY nor SELL conditions are met."
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
                        html.H4("Open Positions"),
                        html.P(id="positions-display", className="metric-value neutral"),
                    ]
                ),
                html.Div(
                    className="metric-card",
                    children=[
                        html.H4("Risk-Free Return (Benchmark)"),
                        html.P(f"{benchmark_return:.2f}%", className="metric-value neutral"),
                    ]
                ),
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

# Callback: update strategy data with PNL color
@app.callback(
    [Output("equity-display", "children"),
     Output("pnl-display", "children"),
     Output("pnl-display", "className"),
     Output("positions-display", "children")],
    [Input("interval", "n_intervals")]
)
def update_strategy_data(n):
    global current_balance, current_pnl, open_positions
    
    equity = f"${current_balance:.2f}"
    pnl = f"${current_pnl:.2f}"
    
    # Determine PNL class based on value
    if current_pnl > 0:
        pnl_class = "metric-value positive"
    elif current_pnl < 0:
        pnl_class = "metric-value negative"
    else:
        pnl_class = "metric-value neutral"
        
    positions = f"{len(open_positions)} Open Positions"
    
    return equity, pnl, pnl_class, positions

# Callback: kill switch to close all trades and update status
@app.callback(
    [Output("kill-switch", "children"),
     Output("kill-switch", "className"),
     Output("status-indicator", "className"),
     Output("status-text", "children")],
    [Input("kill-switch", "n_clicks")]
)
def kill_switch(n_clicks):
    global kill_switch_triggered, open_positions
    
    if n_clicks > 0:
        kill_switch_triggered = True
        close_all_trades(client, account_id)  # Close all trades
        open_positions = []  # Reset open positions to empty
        return ("Kill Switch Triggered: All Trades Closed", 
                "kill-switch triggered", 
                "status-indicator status-inactive", 
                "Strategy Stopped")
    
    return ("Kill Switch: Close All Trades", 
            "kill-switch", 
            "status-indicator", 
            "Strategy Active")

# Callback: update performance chart based on time range
@app.callback(
    Output("performance-chart", "figure"),
    [Input("time-range-dropdown", "value"),
     Input("interval", "n_intervals")]
)
def update_performance_chart(time_range, n):
    global strategy_returns, timestamps, benchmark_return

    # Filter data based on selected time range
    current_time = time.time()
    filtered_indices = [i for i, t in enumerate(timestamps) if current_time - t <= time_range]
    filtered_timestamps = [timestamps[i] for i in filtered_indices]
    filtered_returns = [strategy_returns[i] for i in filtered_indices]

    # Convert timestamps to readable format
    readable_timestamps = [time.strftime("%H:%M:%S", time.localtime(t)) for t in filtered_timestamps]

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

    # Add benchmark returns as a horizontal line
    fig.add_trace(go.Scatter(
        x=readable_timestamps,
        y=[benchmark_return] * len(readable_timestamps),  # Benchmark is a constant value
        mode='lines',
        name="Benchmark (Risk-Free Rate)",
        line=dict(color='#e74c3c', width=2, dash='dot')
    ))

    # Update layout with better styling
    fig.update_layout(
        title="Strategy Returns vs Benchmark",
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