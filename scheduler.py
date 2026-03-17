import asyncio
import logging
import uuid
from datetime import datetime
from typing import AsyncGenerator

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from schemas import BriefingRecord
from services import briefing_store, llm_engine, market_data, news_collector, news_filter, portfolio_manager, stats_tracker

logger = logging.getLogger(__name__)

_lock = asyncio.Lock()
_scheduler: AsyncIOScheduler | None = None


async def run_pipeline(lang: str = "ko", client_id: str = "") -> AsyncGenerator[dict, None]:
    """브리핑 생성 파이프라인. SSE 이벤트를 yield한다."""
    if _lock.locked():
        yield {"type": "error", "message": "Already generating a briefing. Please wait."}
        return

    async with _lock:
        try:
            # Step 1: 뉴스 + 시장 데이터 병렬 수집
            yield {"type": "progress", "step": 1, "message": "뉴스 수집 중..."}
            raw_news, snapshot = await asyncio.gather(
                news_collector.collect_all(),
                market_data.get_snapshot(),
            )

            # Step 2: 뉴스 필터링
            yield {"type": "progress", "step": 2, "message": "뉴스 필터링 중..."}
            filtered_news = news_filter.filter_news(raw_news)
            news_text = news_filter.format_for_llm(filtered_news)

            # Step 3: 시장 데이터 포맷 + 포트폴리오 로드
            yield {"type": "progress", "step": 3, "message": "시장 데이터 처리 중..."}
            market_text = market_data.format_for_llm(snapshot)
            portfolio = await portfolio_manager.get_portfolio(client_id)
            portfolio_text = portfolio_manager.format_for_llm(portfolio)

            # Step 4: AI 분석
            yield {"type": "progress", "step": 4, "message": "AI 브리핑 생성 중..."}
            content, model_name, elapsed_ms = await llm_engine.generate_briefing(
                news_text, market_text, portfolio_text, lang
            )

            # 저장
            now = datetime.now()
            record = BriefingRecord(
                id=str(uuid.uuid4())[:8],
                date=now.strftime("%Y-%m-%d"),
                generatedAt=now.isoformat(),
                content=content,
                model=model_name,
                newsCount=len(filtered_news),
                generationTimeMs=elapsed_ms,
                preview=content[:100].replace("\n", " "),
            )
            await briefing_store.save_briefing(record)
            await stats_tracker.record_api_call()
            logger.info("[Scheduler] API 호출 집계 완료")

            yield {"type": "complete", "briefing": record.model_dump()}

        except Exception as e:
            logger.exception(f"[Scheduler] 파이프라인 오류: {e}")
            yield {"type": "error", "message": str(e)}


async def _scheduled_run() -> None:
    """APScheduler에 의해 매일 실행."""
    logger.info("[Scheduler] 자동 브리핑 생성 시작")
    async for event in run_pipeline(client_id=""):
        if event.get("type") == "complete":
            logger.info("[Scheduler] 자동 브리핑 생성 완료")
        elif event.get("type") == "error":
            logger.error(f"[Scheduler] 자동 브리핑 오류: {event.get('message')}")


def start_scheduler() -> None:
    global _scheduler
    cron_parts = settings.briefing_cron.split()
    if len(cron_parts) != 5:
        logger.warning(f"[Scheduler] 잘못된 cron 표현식: {settings.briefing_cron}")
        return

    minute, hour, day, month, day_of_week = cron_parts
    _scheduler = AsyncIOScheduler(timezone=settings.tz)
    _scheduler.add_job(
        _scheduled_run,
        "cron",
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
        id="daily_briefing",
    )
    _scheduler.start()
    logger.info(f"[Scheduler] 시작 — 스케줄: {settings.briefing_cron} ({settings.tz})")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] 종료")
