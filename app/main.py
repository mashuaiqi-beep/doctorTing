import uvicorn
from fastapi import FastAPI

from app.api.triage_api import router as triage_router

app = FastAPI(
    title="Medical Triage Agent",
    description="一个用于演示医疗问诊分诊 Agent 的小项目。",
    version="0.1.0",
)

app.include_router(triage_router)


@app.get("/")
def root() -> dict:
    """根路径接口。"""

    return {"message": "医疗问诊分诊 Agent 已启动。"}


@app.get("/health")
def health_check() -> dict:
    """健康检查接口。"""

    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
