from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from backtest import run_backtest, get_available_symbols, get_max_candles
from binance_api import BinanceAPI
from typing import Dict, Optional, List
from pydantic import BaseModel
import logging
import os
import sys
import traceback
import json
import asyncio

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Log startup information
logger.info("Starting application...")
logger.info(f"Python version: {sys.version}")
logger.info(f"Environment variables: RAILWAY_ENVIRONMENT={os.environ.get('RAILWAY_ENVIRONMENT')}")

app = FastAPI()

# Add CORS middleware for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you might want to restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Check if we're running in production (Railway)
is_production = os.environ.get('RAILWAY_ENVIRONMENT') == 'production'
logger.info(f"Running in production mode: {is_production}")

try:
    # Mount static files with proper configuration
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    logger.info(f"Mounting static files from: {static_dir}")
    
    # Check if static directory exists
    if not os.path.exists(static_dir):
        logger.warning(f"Static directory not found: {static_dir}")
        # Create the directory if it doesn't exist
        os.makedirs(static_dir, exist_ok=True)
        logger.info(f"Created static directory: {static_dir}")
    
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    logger.info(f"Loading templates from: {templates_dir}")
    
    # Check if templates directory exists
    if not os.path.exists(templates_dir):
        logger.warning(f"Templates directory not found: {templates_dir}")
        # Create the directory if it doesn't exist
        os.makedirs(templates_dir, exist_ok=True)
        logger.info(f"Created templates directory: {templates_dir}")
    
    templates = Jinja2Templates(directory=templates_dir)
except Exception as e:
    logger.error(f"Error setting up static files or templates: {str(e)}")
    logger.error(traceback.format_exc())
    # Don't raise the exception, just log it and continue
    # This allows the app to start even if there are issues with static files
    logger.warning("Continuing without static files or templates")

# Initialize Binance API client
binance_api = BinanceAPI(
    api_key=os.environ.get('BINANCE_API_KEY'),
    api_secret=os.environ.get('BINANCE_API_SECRET')
)

# Define the request model
class BacktestParams(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    limit: int = 500
    strategy_params: Dict = {}

# Parameter descriptions
PARAM_DESCRIPTIONS = {
    "symbol": "The trading pair to backtest (e.g., BTC/USDT)",
    "timeframe": "The candle timeframe for the backtest",
    "limit": "Number of candles to analyze",
    "swing_period": "Period for identifying swing highs and lows",
    "external_liquidity_period": "Period for calculating external liquidity levels",
    "liquidity_threshold": "Threshold for identifying liquidity zones (0.99 = 1% from high/low)",
    "sweep_period": "Period for identifying liquidity sweeps",
    "mss_threshold": "Threshold for Market Structure Shift detection (1.5 = 50% above average)",
    "tp_period": "Period for calculating take profit levels"
}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    try:
        # Pass the scheme to the template
        scheme = "https" if is_production else request.url.scheme
        logger.info(f"Serving root with scheme: {scheme}")
        
        # Check if template exists
        template_path = os.path.join(templates_dir, "index.html")
        if not os.path.exists(template_path):
            logger.error(f"Template file not found: {template_path}")
            # Try to use the fallback template
            fallback_path = os.path.join(templates_dir, "fallback.html")
            if os.path.exists(fallback_path):
                logger.info(f"Using fallback template: {fallback_path}")
                with open(fallback_path, "r") as f:
                    return HTMLResponse(content=f.read())
            else:
                return HTMLResponse(content="<h1>Error: Template file not found</h1>", status_code=500)
        
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request,
                "scheme": scheme
            }
        )
    except Exception as e:
        logger.error(f"Error serving root: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a simple HTML error page instead of raising an exception
        return HTMLResponse(
            content=f"""
            <html>
                <head>
                    <title>Error</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; }}
                        h1 {{ color: #e74c3c; }}
                        pre {{ background: #f8f9fa; padding: 10px; border-radius: 5px; }}
                    </style>
                </head>
                <body>
                    <h1>Internal Server Error</h1>
                    <p>The application encountered an error while processing your request.</p>
                    <p>Error details: {str(e)}</p>
                    <p>Please check the <a href="/health">health check</a> for more information.</p>
                </body>
            </html>
            """,
            status_code=500
        )

@app.get("/api/symbols")
async def get_symbols():
    try:
        symbols = get_available_symbols()
        logger.info(f"Returning {len(symbols)} symbols")
        return symbols
    except Exception as e:
        logger.error(f"Error in get_symbols: {str(e)}")
        logger.error(traceback.format_exc())
        return ["BTC/USDT"]

@app.get("/api/max-candles/{symbol}/{timeframe}")
async def get_max_candles_for_symbol(symbol: str, timeframe: str):
    try:
        # Convert the URL-safe symbol back to the exchange format
        exchange_symbol = symbol.replace('-', '/')
        max_candles = get_max_candles(exchange_symbol, timeframe)
        logger.info(f"Max candles for {exchange_symbol} on {timeframe}: {max_candles}")
        return {"max_candles": max_candles}
    except Exception as e:
        logger.error(f"Error in get_max_candles_for_symbol: {str(e)}")
        logger.error(traceback.format_exc())
        return {"max_candles": 500}

@app.get("/api/parameter-descriptions")
async def get_parameter_descriptions():
    try:
        logger.info("Returning parameter descriptions")
        return PARAM_DESCRIPTIONS
    except Exception as e:
        logger.error(f"Error getting parameter descriptions: {str(e)}")
        logger.error(traceback.format_exc())
        return PARAM_DESCRIPTIONS

@app.post("/backtest")
async def run_backtest_endpoint(params: BacktestParams):
    try:
        logger.info(f"Running backtest with params: {params}")
        results = run_backtest(params.dict())
        
        # Ensure the response has all required fields
        if not isinstance(results, dict):
            results = {}
            
        # Set default values for missing fields
        default_response = {
            'total_trades': 0,
            'win_rate': 0.0,
            'avg_r': 0.0,
            'profit_factor': 0.0,
            'net_pnl': 0.0,
            'trades': [],
            'parameters_used': params.dict()
        }
        
        # Merge the results with default values
        response = {**default_response, **results}
        
        # Ensure numeric values are properly formatted
        response['win_rate'] = float(response.get('win_rate', 0))
        response['avg_r'] = float(response.get('avg_r', 0))
        response['profit_factor'] = float(response.get('profit_factor', 0))
        response['net_pnl'] = float(response.get('net_pnl', 0))
        
        return response
    except Exception as e:
        logger.error(f"Error in backtest: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'total_trades': 0,
            'win_rate': 0.0,
            'avg_r': 0.0,
            'profit_factor': 0.0,
            'net_pnl': 0.0,
            'trades': [],
            'error': str(e)
        }

@app.get("/metrics")
async def get_metrics(params: Optional[Dict] = None):
    try:
        logger.info(f"Getting metrics with params: {params}")
        results = run_backtest(params)
        return {
            "total_trades": results['total_trades'],
            "win_rate": results['win_rate'],
            "avg_r": results['avg_r'],
            "profit_factor": results['profit_factor'],
            "net_pnl": results['net_pnl']
        }
    except Exception as e:
        logger.error(f"Error in get_metrics: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

@app.get("/health")
async def health_check():
    try:
        # Check if static directory exists
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        static_exists = os.path.exists(static_dir)
        
        # Check if templates directory exists
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        templates_exists = os.path.exists(templates_dir)
        
        # Check if key files exist
        script_exists = os.path.exists(os.path.join(static_dir, "script.js"))
        styles_exists = os.path.exists(os.path.join(static_dir, "styles.css"))
        index_exists = os.path.exists(os.path.join(templates_dir, "index.html"))
        
        # Get directory listing
        static_files = os.listdir(static_dir) if static_exists else []
        template_files = os.listdir(templates_dir) if templates_exists else []
        
        return {
            "status": "ok",
            "environment": {
                "is_production": is_production,
                "python_version": sys.version,
                "railway_environment": os.environ.get('RAILWAY_ENVIRONMENT'),
                "working_directory": os.getcwd(),
                "app_directory": os.path.dirname(__file__)
            },
            "files": {
                "static_dir_exists": static_exists,
                "templates_dir_exists": templates_exists,
                "script_js_exists": script_exists,
                "styles_css_exists": styles_exists,
                "index_html_exists": index_exists,
                "static_files": static_files,
                "template_files": template_files
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

# Create a fallback template if the main template is missing
def create_fallback_template():
    fallback_path = os.path.join(templates_dir, "fallback.html")
    if not os.path.exists(fallback_path):
        with open(fallback_path, "w") as f:
            f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Backtester - Fallback</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            line-height: 1.6;
        }
        h1 {
            color: #3498db;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .info {
            background-color: #d1ecf1;
            color: #0c5460;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Crypto Backtester</h1>
        <div class="error">
            <strong>Warning:</strong> The main template is missing. This is a fallback page.
        </div>
        <div class="info">
            <p>The application is running, but there might be issues with the static files or templates.</p>
            <p>Please check the <a href="/health">health check</a> for more information.</p>
        </div>
        <h2>API Endpoints</h2>
        <ul>
            <li><a href="/api/symbols">/api/symbols</a> - Get available trading pairs</li>
            <li><a href="/api/max-candles/BTC/USDT/1h">/api/max-candles/{symbol}/{timeframe}</a> - Get max candles for a symbol</li>
            <li><a href="/api/parameter-descriptions">/api/parameter-descriptions</a> - Get parameter descriptions</li>
            <li><a href="/health">/health</a> - Health check</li>
        </ul>
    </div>
</body>
</html>
            """)
        logger.info(f"Created fallback template: {fallback_path}")
    return fallback_path

# Create fallback template if needed
try:
    create_fallback_template()
except Exception as e:
    logger.error(f"Error creating fallback template: {str(e)}")
    logger.error(traceback.format_exc())

# Binance API endpoints
@app.get("/api/binance/markets")
async def get_binance_markets():
    """Get all available markets from Binance"""
    try:
        return await binance_api.fetch_markets()
    except Exception as e:
        logger.error(f"Error fetching Binance markets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/binance/ticker/{symbol}")
async def get_binance_ticker(symbol: str):
    """Get current ticker for a symbol"""
    try:
        return await binance_api.fetch_ticker(symbol)
    except Exception as e:
        logger.error(f"Error fetching Binance ticker for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/binance/ohlcv/{symbol}")
async def get_binance_ohlcv(symbol: str, timeframe: str = "1h", limit: int = 100):
    """Get OHLCV data for a symbol"""
    try:
        return await binance_api.fetch_ohlcv(symbol, timeframe, limit)
    except Exception as e:
        logger.error(f"Error fetching Binance OHLCV for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/binance/balance")
async def get_binance_balance():
    """Get account balance"""
    try:
        return await binance_api.fetch_balance()
    except Exception as e:
        logger.error(f"Error fetching Binance balance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class OrderRequest(BaseModel):
    symbol: str
    order_type: str
    side: str
    amount: float
    price: Optional[float] = None

@app.post("/api/binance/order")
async def create_binance_order(order: OrderRequest):
    """Create a new order"""
    try:
        return await binance_api.create_order(
            order.symbol,
            order.order_type,
            order.side,
            order.amount,
            order.price
        )
    except Exception as e:
        logger.error(f"Error creating Binance order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/binance/order/{order_id}")
async def get_binance_order(order_id: str, symbol: str):
    """Get order details"""
    try:
        return await binance_api.fetch_order(order_id, symbol)
    except Exception as e:
        logger.error(f"Error fetching Binance order {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/binance/order/{order_id}")
async def cancel_binance_order(order_id: str, symbol: str):
    """Cancel an order"""
    try:
        return await binance_api.cancel_order(order_id, symbol)
    except Exception as e:
        logger.error(f"Error canceling Binance order {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/binance/open-orders")
async def get_binance_open_orders(symbol: Optional[str] = None):
    """Get open orders"""
    try:
        return await binance_api.fetch_open_orders(symbol)
    except Exception as e:
        logger.error(f"Error fetching Binance open orders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/binance/trades/{symbol}")
async def get_binance_trades(symbol: str, since: Optional[int] = None, limit: Optional[int] = None):
    """Get trade history"""
    try:
        return await binance_api.fetch_my_trades(symbol, since, limit)
    except Exception as e:
        logger.error(f"Error fetching Binance trades for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/binance/deposit-address/{code}")
async def get_binance_deposit_address(code: str):
    """Get deposit address for a currency"""
    try:
        return await binance_api.fetch_deposit_address(code)
    except Exception as e:
        logger.error(f"Error fetching Binance deposit address for {code}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/binance/withdrawals/{code}")
async def get_binance_withdrawals(code: str, since: Optional[int] = None, limit: Optional[int] = None):
    """Get withdrawal history"""
    try:
        return await binance_api.fetch_withdrawals(code, since, limit)
    except Exception as e:
        logger.error(f"Error fetching Binance withdrawals for {code}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[str, List[WebSocket]] = {
            'orderbook': {},
            'trades': {},
            'ticker': {},
            'ohlcv': {},
            'balance': {},
            'orders': {},
            'my_trades': {}
        }

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        # Remove from all subscriptions
        for channel in self.subscriptions.values():
            for symbol in list(channel.keys()):
                if websocket in channel[symbol]:
                    channel[symbol].remove(websocket)
                    if not channel[symbol]:
                        del channel[symbol]

    async def subscribe(self, websocket: WebSocket, channel: str, symbol: str):
        if symbol not in self.subscriptions[channel]:
            self.subscriptions[channel][symbol] = []
        self.subscriptions[channel][symbol].append(websocket)

    async def unsubscribe(self, websocket: WebSocket, channel: str, symbol: str):
        if symbol in self.subscriptions[channel]:
            self.subscriptions[channel][symbol].remove(websocket)
            if not self.subscriptions[channel][symbol]:
                del self.subscriptions[channel][symbol]

    async def broadcast(self, channel: str, symbol: str, message: Dict):
        if symbol in self.subscriptions[channel]:
            for connection in self.subscriptions[channel][symbol]:
                try:
                    await connection.send_json(message)
                except:
                    await self.disconnect(connection)

manager = ConnectionManager()

# WebSocket endpoints
@app.websocket("/ws/orderbook/{symbol}")
async def websocket_orderbook(websocket: WebSocket, symbol: str):
    await manager.connect(websocket)
    try:
        await manager.subscribe(websocket, 'orderbook', symbol)
        while True:
            try:
                orderbook = await binance_api.watch_orderbook(symbol)
                await manager.broadcast('orderbook', symbol, orderbook)
            except Exception as e:
                logger.error(f"Error in orderbook websocket: {str(e)}")
                break
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        await manager.unsubscribe(websocket, 'orderbook', symbol)

@app.websocket("/ws/trades/{symbol}")
async def websocket_trades(websocket: WebSocket, symbol: str):
    await manager.connect(websocket)
    try:
        await manager.subscribe(websocket, 'trades', symbol)
        while True:
            try:
                trades = await binance_api.watch_trades(symbol)
                await manager.broadcast('trades', symbol, trades)
            except Exception as e:
                logger.error(f"Error in trades websocket: {str(e)}")
                break
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        await manager.unsubscribe(websocket, 'trades', symbol)

@app.websocket("/ws/ticker/{symbol}")
async def websocket_ticker(websocket: WebSocket, symbol: str):
    await manager.connect(websocket)
    try:
        await manager.subscribe(websocket, 'ticker', symbol)
        while True:
            try:
                ticker = await binance_api.watch_ticker(symbol)
                await manager.broadcast('ticker', symbol, ticker)
            except Exception as e:
                logger.error(f"Error in ticker websocket: {str(e)}")
                break
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        await manager.unsubscribe(websocket, 'ticker', symbol)

@app.websocket("/ws/ohlcv/{symbol}")
async def websocket_ohlcv(websocket: WebSocket, symbol: str, timeframe: str = "1m"):
    await manager.connect(websocket)
    try:
        await manager.subscribe(websocket, 'ohlcv', symbol)
        while True:
            try:
                ohlcv = await binance_api.watch_ohlcv(symbol, timeframe)
                await manager.broadcast('ohlcv', symbol, ohlcv)
            except Exception as e:
                logger.error(f"Error in OHLCV websocket: {str(e)}")
                break
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        await manager.unsubscribe(websocket, 'ohlcv', symbol)

@app.websocket("/ws/balance")
async def websocket_balance(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await manager.subscribe(websocket, 'balance', 'global')
        while True:
            try:
                balance = await binance_api.watch_balance()
                await manager.broadcast('balance', 'global', balance)
            except Exception as e:
                logger.error(f"Error in balance websocket: {str(e)}")
                break
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        await manager.unsubscribe(websocket, 'balance', 'global')

@app.websocket("/ws/orders")
async def websocket_orders(websocket: WebSocket, symbol: Optional[str] = None):
    await manager.connect(websocket)
    try:
        await manager.subscribe(websocket, 'orders', symbol or 'global')
        while True:
            try:
                orders = await binance_api.watch_orders(symbol)
                await manager.broadcast('orders', symbol or 'global', orders)
            except Exception as e:
                logger.error(f"Error in orders websocket: {str(e)}")
                break
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        await manager.unsubscribe(websocket, 'orders', symbol or 'global')

@app.websocket("/ws/my-trades")
async def websocket_my_trades(websocket: WebSocket, symbol: Optional[str] = None):
    await manager.connect(websocket)
    try:
        await manager.subscribe(websocket, 'my_trades', symbol or 'global')
        while True:
            try:
                trades = await binance_api.watch_my_trades(symbol)
                await manager.broadcast('my_trades', symbol or 'global', trades)
            except Exception as e:
                logger.error(f"Error in my trades websocket: {str(e)}")
                break
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        await manager.unsubscribe(websocket, 'my_trades', symbol or 'global')
