import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import scheduler as sched
from config import settings
from schemas import ApiResponse, Portfolio
from services import briefing_store, market_data, portfolio_manager, stats_tracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    sched.start_scheduler()
    yield
    sched.stop_scheduler()


app = FastAPI(title="AI 모닝 마켓 브리핑", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def track_visits(request: Request, call_next):
    # 정적 자산·API 제외하고 페이지 방문만 집계
    if request.url.path in ("/", "") or (
        not request.url.path.startswith("/api/")
        and not request.url.path.startswith("/css/")
        and not request.url.path.startswith("/js/")
        and not request.url.path.startswith("/icons/")
        and not request.url.path.endswith((".json", ".js", ".css", ".png", ".ico"))
    ):
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        ip = ip.split(",")[0].strip()
        asyncio.create_task(stats_tracker.record_visit(ip))
    return await call_next(request)


# ===== SSE 브리핑 생성 =====
@app.get("/api/briefing/generate/stream")
async def briefing_stream(request: Request, lang: str = "ko"):
    async def generate():
        async for event in sched.run_pipeline(lang=lang):
            if await request.is_disconnected():
                logger.info("[SSE] 클라이언트 연결 해제")
                break
            event_type = event.get("type", "message")
            # 프론트엔드가 named event 방식(addEventListener)을 사용하므로 event: 헤더 포함
            if event_type == "complete":
                asyncio.create_task(stats_tracker.record_api_call())
            yield f"event: {event_type}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ===== 브리핑 API =====
@app.get("/api/briefing/latest")
async def get_latest_briefing():
    record = briefing_store.load_latest()
    if record is None:
        return JSONResponse({"data": None, "message": "브리핑이 없습니다."})
    return {"data": record.model_dump()}


@app.get("/api/briefing/history")
async def get_briefing_history(limit: int = 20):
    records = briefing_store.list_briefings(limit=limit)
    return {"data": [r.model_dump() for r in records]}


@app.get("/api/briefing/{briefing_id}")
async def get_briefing_by_id(briefing_id: str):
    record = briefing_store.load_by_id(briefing_id)
    if record is None:
        return JSONResponse({"data": None, "message": "브리핑을 찾을 수 없습니다."}, status_code=404)
    return {"data": record.model_dump()}


# ===== 시장 데이터 =====
@app.get("/api/market/snapshot")
async def get_market_snapshot():
    try:
        snapshot = await market_data.get_snapshot()
        return {"data": snapshot}
    except Exception as e:
        logger.error(f"[Market] 스냅샷 오류: {e}")
        return JSONResponse({"data": None, "message": str(e)}, status_code=500)


# ===== 포트폴리오 =====
@app.get("/api/portfolio")
async def get_portfolio():
    portfolio = portfolio_manager.get_portfolio()
    return {"data": portfolio.model_dump()}


@app.post("/api/portfolio")
async def save_portfolio(portfolio: Portfolio):
    portfolio_manager.save_portfolio(portfolio)
    return {"data": portfolio.model_dump(), "message": "포트폴리오가 저장되었습니다."}


# ===== 설정 =====
@app.get("/api/settings")
async def get_settings():
    return {
        "data": {
            "llmProvider": settings.llm_provider,
            "llmModel": settings.llm_model,
            "llmFallbackModel": settings.llm_fallback_model,
            "briefingCron": settings.briefing_cron,
            "maxBriefings": settings.max_briefings,
            "timezone": settings.tz,
        }
    }


# ===== 상태 =====
@app.get("/api/status")
async def get_status():
    return {
        "data": {
            "status": "online",
            "scheduler": sched._scheduler.running if sched._scheduler else False,
        }
    }


# ===== 통계 =====
@app.get("/api/stats")
async def get_stats():
    return {"data": await stats_tracker.get_stats()}


# ===== 정적 파일 & SPA 폴백 =====
app.mount("/css", StaticFiles(directory="public/css"), name="css")
app.mount("/js", StaticFiles(directory="public/js"), name="js")
app.mount("/icons", StaticFiles(directory="public/icons"), name="icons")


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    from fastapi.responses import FileResponse
    return FileResponse("public/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=True)
