"""
방문자 수 및 API 호출 횟수 집계.
- Upstash Redis REST API로 영구 저장 (서버 재시작 무관)
- Redis 미설정 시 in-memory fallback
- 오늘 집계: 매일 KST 자정 자동 초기화 (key TTL)
- 누적 집계: 영구 유지
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

import httpx

from config import settings

logger = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))

# In-memory fallback (Redis 미설정 시)
_mem = {"visitors": {}, "api": {"daily": {}, "total": 0}}

# 쿨다운: IP별 마지막 방문 시각 (in-memory fallback용)
_visit_cooldown: dict[str, float] = {}
_COOLDOWN_SECONDS = 600  # 10분


def _today() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _redis_enabled() -> bool:
    return bool(settings.upstash_redis_url and settings.upstash_redis_token)


async def _pipeline(commands: list) -> list:
    """Upstash Redis pipeline 호출. 결과 리스트 반환."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{settings.upstash_redis_url}/pipeline",
                headers={"Authorization": f"Bearer {settings.upstash_redis_token}"},
                json=commands,
            )
            body = r.json()
            if not isinstance(body, list):
                logger.warning(f"[Stats] Redis 비정상 응답: {body}")
                return []
            results = []
            for item in body:
                if isinstance(item, dict) and "error" in item:
                    logger.warning(f"[Stats] Redis 명령 오류: {item['error']}")
                results.append(item.get("result") if isinstance(item, dict) else None)
            return results
    except Exception as e:
        logger.warning(f"[Stats] Redis 호출 실패: {e}")
        return []


async def record_visit(ip: str) -> None:
    """방문 기록 — 같은 IP는 10분 내 재카운트 방지."""
    today = _today()
    cooldown_key = f"stats:cooldown:{ip}"

    if _redis_enabled():
        # SET NX EX: 키가 없을 때만 생성 → 결과가 "OK"이면 첫 방문(또는 쿨다운 만료)
        results = await _pipeline([
            ["SET", cooldown_key, "1", "NX", "EX", _COOLDOWN_SECONDS],
        ])
        if not results or results[0] != "OK":
            return  # 쿨다운 중 — 카운트 건너뜀
        await _pipeline([
            ["INCR", f"stats:visitors:{today}"],
            ["EXPIRE", f"stats:visitors:{today}", 172800],
            ["INCR", "stats:total_visitors"],
        ])
    else:
        import time
        now = time.monotonic()
        if now - _visit_cooldown.get(ip, 0) < _COOLDOWN_SECONDS:
            return  # 쿨다운 중
        _visit_cooldown[ip] = now
        _mem["visitors"][today] = _mem["visitors"].get(today, 0) + 1
        _mem["total_visits"] = _mem.get("total_visits", 0) + 1


async def record_api_call() -> None:
    """브리핑 생성 횟수 증가 (오늘 + 누적)."""
    today = _today()
    if _redis_enabled():
        await _pipeline([
            ["INCR", f"stats:api:{today}"],
            ["EXPIRE", f"stats:api:{today}", 172800],  # 48시간 TTL
            ["INCR", "stats:api:total"],               # 누적 카운터
        ])
    else:
        _mem["api"]["daily"][today] = _mem["api"]["daily"].get(today, 0) + 1
        _mem["api"]["total"] += 1


async def get_stats() -> dict:
    """현재 통계 반환."""
    today = _today()
    if _redis_enabled():
        results = await _pipeline([
            ["GET", f"stats:visitors:{today}"],   # 오늘 방문 횟수
            ["GET", "stats:total_visitors"],       # 누적 방문 횟수
            ["GET", f"stats:api:{today}"],         # 오늘 API 호출
            ["GET", "stats:api:total"],            # 누적 API 호출
        ])
        if results:
            return {
                "todayVisitors": int(results[0] or 0),
                "totalVisitors": int(results[1] or 0),
                "todayApiCalls": int(results[2] or 0),
                "totalApiCalls": int(results[3] or 0),
            }
    # fallback
    return {
        "todayVisitors": _mem["visitors"].get(today, 0),
        "totalVisitors": _mem.get("total_visits", 0),
        "todayApiCalls": _mem["api"]["daily"].get(today, 0),
        "totalApiCalls": _mem["api"]["total"],
    }
