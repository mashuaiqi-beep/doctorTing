from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.triage_api import router as triage_router

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Medical Triage Agent",
    description="一个用于演示医疗问诊分诊 Agent 的小项目。",
    version="0.1.0",
)

app.include_router(triage_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def root() -> HTMLResponse:
    """前端首页。"""

    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    styles_version = int((STATIC_DIR / "styles.css").stat().st_mtime)
    script_version = int((STATIC_DIR / "app.js").stat().st_mtime)
    html = html.replace("__STYLES_VERSION__", str(styles_version))
    html = html.replace("__SCRIPT_VERSION__", str(script_version))
    return HTMLResponse(content=html)


@app.get("/health")
def health_check() -> dict:
    """健康检查接口。"""

    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
