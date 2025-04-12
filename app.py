from fastapi import FastAPI
from backtest import run_backtest

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "BTC Backtester is live!"}

@app.get("/backtest")
def trigger_backtest():
    results = run_backtest()
    return results

@app.get("/metrics")
def get_metrics():
    results = run_backtest()

    return {
        "total_trades": results['total_trades'],
        "win_rate": results['win_rate'],
        "avg_r": results['avg_r'],
        "profit_factor": results['profit_factor'],
        "net_pnl": results['net_pnl']
    }
