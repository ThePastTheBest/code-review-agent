import logging

import uvicorn
from fastapi import FastAPI

from app.api.router import router
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="Code Review Agent",
    description="基于 Claude AI 的自动代码审查服务",
    version="1.0.0",
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Code Review Agent API", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=True,
    )
