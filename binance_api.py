import ccxt
import ccxtpro
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class BinanceAPI:
    """
    Binance API client using CCXT and CCXT Pro.
    
    This class provides access to Binance's public data only.
    No API key is required for any of these methods.
    
    Available methods:
    - fetch_markets: Get all available trading pairs
    - fetch_ticker: Get current price and volume data
    - fetch_ohlcv: Get historical price data (candles)
    - watch_orderbook: Stream real-time order book updates
    - watch_trades: Stream real-time trade data
    - watch_ticker: Stream real-time price updates
    - watch_ohlcv: Stream real-time candle data
    """
    def __init__(self):
        """
        Initialize Binance API client for public data only
        
        Note:
            No API key is required as this client only accesses public endpoints.
        """
        # Initialize REST client
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
        })
        
        # Initialize WebSocket client with CCXT Pro
        self.ws_exchange = ccxtpro.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # or 'future' for futures trading
                'adjustForTimeDifference': True,
                'recvWindow': 60000,
            }
        })
        
        # Cache for WebSocket data
        self._orderbooks = {}
        self._trades = {}
        self._tickers = {}
        self._ohlcv = {}
        
    async def close(self):
        """Close WebSocket connections"""
        await self.ws_exchange.close()
        
    # ===== PUBLIC METHODS (NO API KEY REQUIRED) =====
    
    async def fetch_markets(self) -> List[Dict]:
        """
        Fetch all available markets (public endpoint, no API key required)
        
        Returns:
            List of market information dictionaries
        """
        try:
            return self.exchange.fetch_markets()
        except Exception as e:
            logger.error(f"Error fetching markets: {str(e)}")
            raise

    async def fetch_ticker(self, symbol: str) -> Dict:
        """
        Fetch current ticker for a symbol (public endpoint, no API key required)
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Ticker information dictionary
        """
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {str(e)}")
            raise

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List[Union[int, float]]]:
        """
        Fetch OHLCV data for a symbol (public endpoint, no API key required)
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1m', '5m', '15m', '1h', '4h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV candles [timestamp, open, high, low, close, volume]
        """
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {str(e)}")
            raise
            
    # WebSocket Public Methods
    async def watch_orderbook(self, symbol: str, limit: int = 20) -> Dict:
        """
        Watch order book for a symbol (public endpoint, no API key required)
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            limit: Maximum number of orders to return
            
        Returns:
            Order book dictionary with bids and asks
        """
        try:
            return await self.ws_exchange.watch_order_book(symbol, limit)
        except Exception as e:
            logger.error(f"Error watching orderbook for {symbol}: {str(e)}")
            raise
            
    async def watch_trades(self, symbol: str, since: Optional[int] = None, limit: Optional[int] = None) -> List[Dict]:
        """
        Watch trades for a symbol (public endpoint, no API key required)
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            since: Optional timestamp to start from
            limit: Optional maximum number of trades to return
            
        Returns:
            List of trade dictionaries
        """
        try:
            return await self.ws_exchange.watch_trades(symbol, since, limit)
        except Exception as e:
            logger.error(f"Error watching trades for {symbol}: {str(e)}")
            raise
            
    async def watch_ticker(self, symbol: str) -> Dict:
        """
        Watch ticker for a symbol (public endpoint, no API key required)
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Ticker information dictionary
        """
        try:
            return await self.ws_exchange.watch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error watching ticker for {symbol}: {str(e)}")
            raise
            
    async def watch_ohlcv(self, symbol: str, timeframe: str = '1m', since: Optional[int] = None, limit: Optional[int] = None) -> List[List[Union[int, float]]]:
        """
        Watch OHLCV for a symbol (public endpoint, no API key required)
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1m', '5m', '15m', '1h', '4h', '1d')
            since: Optional timestamp to start from
            limit: Optional maximum number of candles to return
            
        Returns:
            List of OHLCV candles [timestamp, open, high, low, close, volume]
        """
        try:
            return await self.ws_exchange.watch_ohlcv(symbol, timeframe, since, limit)
        except Exception as e:
            logger.error(f"Error watching OHLCV for {symbol}: {str(e)}")
            raise 