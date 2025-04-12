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
