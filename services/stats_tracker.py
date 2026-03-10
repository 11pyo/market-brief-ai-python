"""
방문자 수 및 API 호출 횟수 집계.
- IP 기준 일별 unique 방문자
- 브리핑 생성 횟수(API 호출)
- data/stats.json 에 영속 저장
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

STATS_FILE = Path("data/stats.json")
KST = timezone(timedelta(hours=9))


def _today() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _load() -> dict:
    if STATS_FILE.exists():
        try:
            return json.loads(STATS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"visitors": {}, "api_calls": {"daily": {}, "total": 0}}


def _save(data: dict) -> None:
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def record_visit(ip: str) -> None:
    """방문 IP 기록 (일별 unique)."""
    try:
        data = _load()
        today = _today()
        daily = data["visitors"].setdefault(today, [])
        if ip not in daily:
            daily.append(ip)
        # 7일치만 보관
        cutoff = (datetime.now(KST) - timedelta(days=7)).strftime("%Y-%m-%d")
        data["visitors"] = {d: v for d, v in data["visitors"].items() if d >= cutoff}
        _save(data)
    except Exception as e:
        logger.warning(f"[Stats] 방문 기록 실패: {e}")


def record_api_call() -> None:
    """브리핑 생성(API 호출) 횟수 증가."""
    try:
        data = _load()
        today = _today()
        data["api_calls"]["daily"][today] = data["api_calls"]["daily"].get(today, 0) + 1
        data["api_calls"]["total"] = data["api_calls"].get("total", 0) + 1
        _save(data)
    except Exception as e:
        logger.warning(f"[Stats] API 호출 기록 실패: {e}")


def get_stats() -> dict:
    """현재 통계 반환."""
    try:
        data = _load()
        today = _today()
        today_visitors = len(data["visitors"].get(today, []))
        total_visitors = sum(len(v) for v in data["visitors"].values())
        today_api = data["api_calls"]["daily"].get(today, 0)
        total_api = data["api_calls"].get("total", 0)
        return {
            "todayVisitors": today_visitors,
            "totalVisitors": total_visitors,
            "todayApiCalls": today_api,
            "totalApiCalls": total_api,
        }
    except Exception as e:
        logger.warning(f"[Stats] 통계 조회 실패: {e}")
        return {"todayVisitors": 0, "totalVisitors": 0, "todayApiCalls": 0, "totalApiCalls": 0}
