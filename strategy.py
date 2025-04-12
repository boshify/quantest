import pandas as pd
from typing import Dict

def ict_strategy(df: pd.DataFrame, params: Dict = None):
    if params is None:
        params = {}
    
    df = df.copy()

    # === STEP 1: ACCUMULATION ===
    swing_period = params.get('swing_period', 1)
    df['swing_high'] = (df['high'].shift(swing_period) < df['high']) & (df['high'].shift(-swing_period) < df['high'])
    df['swing_low']  = (df['low'].shift(swing_period) > df['low']) & (df['low'].shift(-swing_period) > df['low'])

    external_period = params.get('external_liquidity_period', 50)
    df['external_high'] = df['high'].rolling(external_period).max()  # external liquidity
    df['external_low'] = df['low'].rolling(external_period).min()

    liquidity_threshold = params.get('liquidity_threshold', 0.99)
    df['near_liquidity'] = (
        (df['high'] >= df['external_high'] * liquidity_threshold) | 
        (df['low'] <= df['external_low'] * (2 - liquidity_threshold))
    )

    # === STEP 2: MANIPULATION ===
    sweep_period = params.get('sweep_period', 3)
    df['sweep_high'] = df['high'] > df['high'].shift(1).rolling(sweep_period).max()
    df['sweep_low'] = df['low'] < df['low'].shift(1).rolling(sweep_period).min()
    
    df['liquidity_sweep'] = df['sweep_high'] | df['sweep_low']

    # === STEP 3: MSS (Structure Shift) ===
    df['body'] = abs(df['close'] - df['open'])
    mss_threshold = params.get('mss_threshold', 1.5)
    df['mss'] = (df['body'] > df['body'].rolling(3).mean() * mss_threshold) & df['liquidity_sweep']

    # === STEP 4: ORDER BLOCK (Last down candle before MSS up) ===
    df['ob'] = (df['mss'] & (df['open'] > df['close']))  # simplified for longs

    df['entry'] = df['mss'].shift(1) & df['ob'].shift(2)  # simplified entry after OB formation
    
    tp_period = params.get('tp_period', 10)
    df['exit'] = df['high'] > df['high'].rolling(tp_period).max().shift(1)  # breakout TP

    return df
