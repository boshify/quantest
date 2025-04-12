from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from backtest import run_backtest, get_available_symbols, get_max_candles
from typing import Dict, Optional, List
from pydantic import BaseModel
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Check if we're running in production (Railway)
is_production = os.environ.get('RAILWAY_ENVIRONMENT') == 'production'

# Mount static files with proper configuration
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
    # Pass the scheme to the template
    scheme = "https" if is_production else request.url.scheme
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
            "scheme": scheme
        }
    )

@app.get("/api/symbols")
async def get_symbols():
    try:
        symbols = get_available_symbols()
        logger.info(f"Returning {len(symbols)} symbols")
        return symbols
    except Exception as e:
        logger.error(f"Error in get_symbols: {str(e)}")
        return ["BTC/USDT"]

@app.get("/api/max-candles/{symbol}/{timeframe}")
async def get_max_candles_for_symbol(symbol: str, timeframe: str):
    try:
        max_candles = get_max_candles(symbol, timeframe)
        logger.info(f"Max candles for {symbol} on {timeframe}: {max_candles}")
        return {"max_candles": max_candles}
    except Exception as e:
        logger.error(f"Error in get_max_candles_for_symbol: {str(e)}")
        return {"max_candles": 500}

@app.get("/api/parameter-descriptions")
async def get_parameter_descriptions():
    try:
        # Get the strategy class
        strategy_class = get_strategy_class()
        
        # Get parameter descriptions from the strategy class
        param_descriptions = {}
        for param_name, param in strategy_class.__annotations__.items():
            if hasattr(param, '__metadata__'):
                for metadata in param.__metadata__:
                    if isinstance(metadata, dict) and 'description' in metadata:
                        param_descriptions[param_name] = metadata['description']
                        break
        
        if not param_descriptions:
            # Fallback to default descriptions if none found
            param_descriptions = {
                'fast_length': 'Number of periods for fast EMA',
                'slow_length': 'Number of periods for slow EMA',
                'signal_length': 'Number of periods for signal line',
                'stop_loss': 'Stop loss percentage (0-100)',
                'take_profit': 'Take profit percentage (0-100)',
                'trailing_stop': 'Trailing stop percentage (0-100)',
                'position_size': 'Position size as percentage of capital (0-100)',
                'max_positions': 'Maximum number of concurrent positions',
                'risk_per_trade': 'Risk per trade as percentage of capital (0-100)',
                'max_drawdown': 'Maximum drawdown percentage (0-100)',
                'timeframe': 'Trading timeframe (1m, 5m, 15m, 1h, 4h, 1d)',
                'limit': 'Number of candles to analyze'
            }
        
        return param_descriptions
    except Exception as e:
        logger.error(f"Error getting parameter descriptions: {str(e)}")
        # Return default descriptions on error
        return {
            'fast_length': 'Number of periods for fast EMA',
            'slow_length': 'Number of periods for slow EMA',
            'signal_length': 'Number of periods for signal line',
            'stop_loss': 'Stop loss percentage (0-100)',
            'take_profit': 'Take profit percentage (0-100)',
            'trailing_stop': 'Trailing stop percentage (0-100)',
            'position_size': 'Position size as percentage of capital (0-100)',
            'max_positions': 'Maximum number of concurrent positions',
            'risk_per_trade': 'Risk per trade as percentage of capital (0-100)',
            'max_drawdown': 'Maximum drawdown percentage (0-100)',
            'timeframe': 'Trading timeframe (1m, 5m, 15m, 1h, 4h, 1d)',
            'limit': 'Number of candles to analyze'
        }

@app.post("/backtest")
async def run_backtest_endpoint(params: BacktestParams):
    try:
        logger.info(f"Running backtest with params: {params}")
        results = run_backtest(params.dict())
        return results
    except Exception as e:
        logger.error(f"Error in backtest: {str(e)}")
        return {"error": str(e)}

@app.get("/metrics")
async def get_metrics(params: Optional[Dict] = None):
    try:
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
        return {"error": str(e)}

# Helper function to get strategy class
def get_strategy_class():
    from strategy import ict_strategy
    return ict_strategy.__class__
