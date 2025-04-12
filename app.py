from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from backtest import run_backtest, get_available_symbols, get_max_candles
from typing import Dict, Optional, List
from pydantic import BaseModel
import logging
import os
import sys
import traceback

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
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    logger.info(f"Loading templates from: {templates_dir}")
    templates = Jinja2Templates(directory=templates_dir)
except Exception as e:
    logger.error(f"Error setting up static files or templates: {str(e)}")
    logger.error(traceback.format_exc())
    raise

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
        raise

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
        max_candles = get_max_candles(symbol, timeframe)
        logger.info(f"Max candles for {symbol} on {timeframe}: {max_candles}")
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
        return results
    except Exception as e:
        logger.error(f"Error in backtest: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

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
