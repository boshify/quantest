import pandas as pd
from strategy import ict_strategy
import ccxt
from typing import Dict, Optional

# === Fetch Historical BTC Data from Binance ===
exchange = ccxt.binance()

def fetch_data(symbol='BTC/USDT', timeframe='1h', limit=500):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# === Backtest Strategy Logic ===
def run_backtest(params: Optional[Dict] = None):
    if params is None:
        params = {}
    
    # Default parameters
    default_params = {
        'symbol': 'BTC/USDT',
        'timeframe': '1h',
        'limit': 500,
        'strategy_params': {
            'swing_period': 1,
            'external_liquidity_period': 50,
            'liquidity_threshold': 0.99,
            'sweep_period': 3,
            'mss_threshold': 1.5,
            'tp_period': 10
        }
    }
    
    # Update default parameters with user-provided ones
    params = {**default_params, **params}
    strategy_params = {**default_params['strategy_params'], **params.get('strategy_params', {})}
    
    df = fetch_data(
        symbol=params['symbol'],
        timeframe=params['timeframe'],
        limit=params['limit']
    )
    
    # Pass strategy parameters to the strategy function
    df = ict_strategy(df, strategy_params)

    trades = []
    position = None

    for i in range(len(df)):
        row = df.iloc[i]
        if not position and row['entry']:
            position = {
                'entry_price': row['close'],
                'entry_time': row.name
            }
        elif position and row['exit']:
            exit_price = row['close']
            pnl = exit_price - position['entry_price']
            trades.append({
                'entry_time': position['entry_time'],
                'exit_time': row.name,
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'pnl': pnl
            })
            position = None

    trades_df = pd.DataFrame(trades)

    if trades_df.empty:
        return {'total_trades': 0, 'message': 'No trades found.'}

    # === Calculate Metrics ===
    win_rate = (trades_df['pnl'] > 0).mean()
    avg_r = trades_df['pnl'].mean()
    profit_factor = trades_df['pnl'][trades_df['pnl'] > 0].sum() / abs(
        trades_df['pnl'][trades_df['pnl'] < 0].sum() or 1
    )
    net_pnl = trades_df['pnl'].sum()

    return {
        'total_trades': len(trades_df),
        'win_rate': round(win_rate * 100, 2),
        'avg_r': round(avg_r, 2),
        'profit_factor': round(profit_factor, 2),
        'net_pnl': round(net_pnl, 2),
        'trades': trades_df.to_dict(orient='records'),
        'parameters_used': params
    }

