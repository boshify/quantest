from lumibot.brokers import CCXTBroker
from lumibot.backtesting import CCXTData
from lumibot.strategies import Strategy
from datetime import datetime, timedelta
import pandas as pd

class CryptoStrategy(Strategy):
    def initialize(self):
        # Set the trading parameters
        self.sleeptime = "1H"  # Check every hour
        self.last_trade = None
        self.position = None
        
    def position_sizing(self):
        # Get account value and calculate position size
        cash = self.get_cash()
        return cash * 0.95  # Use 95% of available cash
        
    def get_dates(self):
        # Get the current date and the date 24 hours ago
        today = self.get_datetime()
        yesterday = today - timedelta(days=1)
        return yesterday, today
        
    def on_trading_iteration(self):
        # Get current position
        position = self.get_position("BTC/USDT")
        
        # If we have a position, check if we should sell
        if position is not None:
            # Get the current price
            current_price = self.get_last_price("BTC/USDT")
            
            # If price has increased by 5%, sell
            if current_price > position.entry_price * 1.05:
                self.sell_position(position)
                self.last_trade = "sell"
                
        # If we don't have a position, check if we should buy
        else:
            # Get historical data
            yesterday, today = self.get_dates()
            bars = self.get_historical_prices(
                "BTC/USDT",
                "1H",
                yesterday,
                today
            )
            
            # Calculate simple moving averages
            df = bars.df
            df['SMA20'] = df['close'].rolling(window=20).mean()
            df['SMA50'] = df['close'].rolling(window=50).mean()
            
            # If 20 SMA crosses above 50 SMA, buy
            if df['SMA20'].iloc[-1] > df['SMA50'].iloc[-1] and \
               df['SMA20'].iloc[-2] <= df['SMA50'].iloc[-2]:
                # Calculate position size
                cash = self.get_cash()
                price = self.get_last_price("BTC/USDT")
                quantity = self.position_sizing() / price
                
                # Place the buy order
                self.buy("BTC/USDT", quantity)
                self.last_trade = "buy"

if __name__ == "__main__":
    # Set up the broker
    broker = CCXTBroker(
        exchange_id="binance",
        paper_trading=True
    )
    
    # Set up the data source
    data = CCXTData(
        exchange_id="binance",
        timeframe="1H",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2024, 1, 1)
    )
    
    # Create and run the strategy
    strategy = CryptoStrategy(
        broker=broker,
        budget=10000,
        benchmark_asset="BTC/USDT"
    )
    
    # Run the backtest
    strategy.backtest(
        data=data,
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2024, 1, 1)
    ) 