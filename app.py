from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from backtest import run_backtest
from typing import Dict, Optional
from pydantic import BaseModel

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Define the request model
class BacktestParams(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    limit: int = 500
    strategy_params: Dict = {}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/backtest")
async def trigger_backtest(params: BacktestParams):
    results = run_backtest(params.dict())
    return results

@app.get("/metrics")
async def get_metrics(params: Optional[Dict] = None):
    results = run_backtest(params)
    return {
        "total_trades": results['total_trades'],
        "win_rate": results['win_rate'],
        "avg_r": results['avg_r'],
        "profit_factor": results['profit_factor'],
        "net_pnl": results['net_pnl']
    }
