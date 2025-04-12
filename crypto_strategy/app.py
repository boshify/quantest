from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import uvicorn
from strategy import CryptoStrategy, CCXTBroker, CCXTData

app = FastAPI(title="Crypto Backtesting API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BacktestRequest(BaseModel):
    start_date: str
    end_date: str
    initial_budget: float = 10000
    symbol: str = "BTC/USDT"

@app.get("/")
async def root():
    return {"message": "Crypto Backtesting API is running"}

@app.post("/backtest")
async def run_backtest(request: BacktestRequest):
    try:
        # Parse dates
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
        
        # Set up the broker
        broker = CCXTBroker(
            exchange_id="binance",
            paper_trading=True
        )
        
        # Set up the data source
        data = CCXTData(
            exchange_id="binance",
            timeframe="1H",
            start_date=start_date,
            end_date=end_date
        )
        
        # Create and run the strategy
        strategy = CryptoStrategy(
            broker=broker,
            budget=request.initial_budget,
            benchmark_asset=request.symbol
        )
        
        # Run the backtest
        results = strategy.backtest(
            data=data,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True) 