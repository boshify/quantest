import plotly.graph_objects as go
import pandas as pd

def plot_equity_curve(trades):
    df = pd.DataFrame(trades)
    if df.empty:
        print("No trades to plot.")
        return

    df['cumulative_pnl'] = df['pnl'].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['exit_time'],
        y=df['cumulative_pnl'],
        mode='lines+markers',
        name='Cumulative PnL'
    ))

    fig.update_layout(
        title='Equity Curve',
        xaxis_title='Time',
        yaxis_title='PnL',
        template='plotly_dark'
    )

    fig.show()
