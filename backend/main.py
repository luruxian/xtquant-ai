"""主应用入口"""
from fastapi import FastAPI
from routes import asset, order, position, trade, quote, etf

app = FastAPI(
    title="MiniQMT AI Backend",
    description="后端 API 服务",
    version="1.0.0"
)


@app.get("/")
async def root():
    return {"message": "Welcome to MiniQMT AI Backend"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


app.include_router(asset.router)
app.include_router(order.router)
app.include_router(position.router)
app.include_router(trade.router)
app.include_router(quote.router)
app.include_router(etf.router)
