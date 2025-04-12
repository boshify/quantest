import pandas as pd
from strategy import ict_strategy
import ccxt

# === Fetch Historical BTC Data from Binance ===
exchange = ccxt.binance()

def fetch_data(symbol='BTC/USDT', timeframe='1h', limit=500):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# === Backtest Strategy Logic ===
def run_backtest():
    df = fetch_data()
    df = ict_strategy(df)

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
        'trades': trades_df.to_dict(orient='records')
    }

