import pandas as pd
from strategy import ict_strategy
import ccxt
from typing import Dict, Optional, List, Any
import numpy as np
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the exchange globally
try:
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot',
            'defaultTimeInForce': 'GTC',
            'adjustForTimeDifference': True,
            'recvWindow': 60000
        }
    })
    logger.info("Successfully initialized Binance exchange")
except Exception as e:
    logger.error(f"Failed to initialize Binance exchange: {str(e)}")
    exchange = None

# === Fetch Historical BTC Data from Binance ===
def get_available_symbols() -> List[str]:
    try:
        if exchange is None:
            logger.error("Exchange not initialized")
            return ["BTC/USDT"]
            
        # Load markets
        logger.info("Loading markets from Binance...")
        markets = exchange.load_markets()
        
        # Filter for USDT pairs
        usdt_pairs = [symbol for symbol in markets.keys() if symbol.endswith('/USDT')]
        
        # Sort the pairs
        usdt_pairs.sort()
        
        logger.info(f"Successfully loaded {len(usdt_pairs)} USDT pairs")
        return usdt_pairs
    except Exception as e:
        logger.error(f"Error fetching symbols: {str(e)}")
        return ["BTC/USDT"]  # Fallback to BTC/USDT if there's an error

def get_max_candles(symbol: str, timeframe: str) -> int:
    """Get the maximum number of candles available for a symbol/timeframe"""
    try:
        if exchange is None:
            logger.error("Exchange not initialized")
            return 500
            
        # Fetch OHLCV data with a large limit to get the max available
        logger.info(f"Fetching max candles for {symbol} on {timeframe} timeframe")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=1000)
        max_candles = len(ohlcv)
        logger.info(f"Found {max_candles} candles for {symbol}")
        return max_candles
    except Exception as e:
        logger.error(f"Error fetching max candles for {symbol}: {str(e)}")
        return 500  # Fallback to 500

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

