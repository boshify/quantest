import pandas as pd

def ict_strategy(df):
    df = df.copy()

    # === STEP 1: ACCUMULATION ===
    df['swing_high'] = (df['high'].shift(1) < df['high']) & (df['high'].shift(-1) < df['high'])
    df['swing_low']  = (df['low'].shift(1) > df['low']) & (df['low'].shift(-1) > df['low'])

    df['external_high'] = df['high'].rolling(50).max()  # external liquidity
    df['external_low'] = df['low'].rolling(50).min()

    df['near_liquidity'] = (
        (df['high'] >= df['external_high'] * 0.99) | 
        (df['low'] <= df['external_low'] * 1.01)
    )

    # === STEP 2: MANIPULATION ===
    df['sweep_high'] = df['high'] > df['high'].shift(1).rolling(3).max()
    df['sweep_low'] = df['low'] < df['low'].shift(1).rolling(3).min()
    
    df['liquidity_sweep'] = df['sweep_high'] | df['sweep_low']

    # === STEP 3: MSS (Structure Shift) ===
    df['body'] = abs(df['close'] - df['open'])
    df['mss'] = (df['body'] > df['body'].rolling(3).mean() * 1.5) & df['liquidity_sweep']

    # === STEP 4: ORDER BLOCK (Last down candle before MSS up) ===
    df['ob'] = (df['mss'] & (df['open'] > df['close']))  # simplified for longs

    df['entry'] = df['mss'].shift(1) & df['ob'].shift(2)  # simplified entry after OB formation
    df['exit'] = df['high'] > df['high'].rolling(10).max().shift(1)  # breakout TP

    return df
