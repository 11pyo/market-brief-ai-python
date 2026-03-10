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
            return [item.get("result") for item in r.json()]
    except Exception as e:
        logger.warning(f"[Stats] Redis 호출 실패: {e}")
        return []


async def record_visit(ip: str) -> None:
    """방문 IP 기록 (일별 unique + 누적 HyperLogLog)."""
    today = _today()
    if _redis_enabled():
        await _pipeline([
            ["SADD", f"stats:visitors:{today}", ip],
            ["EXPIRE", f"stats:visitors:{today}", 172800],  # 48시간 TTL
            ["PFADD", "stats:total_visitors", ip],          # 누적 HyperLogLog
        ])
    else:
        daily = _mem["visitors"].setdefault(today, set())
        daily.add(ip)


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
            ["SCARD", f"stats:visitors:{today}"],   # 오늘 방문자 수
            ["PFCOUNT", "stats:total_visitors"],     # 누적 방문자 수
            ["GET", f"stats:api:{today}"],           # 오늘 API 호출
            ["GET", "stats:api:total"],              # 누적 API 호출
        ])
        if results:
            return {
                "todayVisitors": int(results[0] or 0),
                "totalVisitors": int(results[1] or 0),
                "todayApiCalls": int(results[2] or 0),
                "totalApiCalls": int(results[3] or 0),
            }
    # fallback
    today_v = len(_mem["visitors"].get(today, set()))
    total_v = sum(len(v) for v in _mem["visitors"].values())
    return {
        "todayVisitors": today_v,
        "totalVisitors": total_v,
        "todayApiCalls": _mem["api"]["daily"].get(today, 0),
        "totalApiCalls": _mem["api"]["total"],
    }
