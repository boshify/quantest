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
