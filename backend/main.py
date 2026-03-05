from fastapi import FastAPI

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
