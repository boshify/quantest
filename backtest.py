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
            trades.append({
                'entry_time': position['entry_time'],
                'exit_time': row.name,
                'pnl': exit_price - position['entry_price']
            })
            position = None

    return {
        'total_trades': len(trades),
        'trades': trades
    }
