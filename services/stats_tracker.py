"""
방문자 수 및 API 호출 횟수 집계.
- 메모리 카운터 (재시작 전까지 유지, 항상 작동)
- data/stats.json 파일 백업 (가능한 경우)
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

STATS_FILE = Path("data/stats.json")
KST = timezone(timedelta(hours=9))

# 메모리 카운터 (서버 프로세스 생존 중 누적)
_mem: dict = {
    "visitors": {},   # {날짜: set(ip)}
    "api_calls": {"daily": {}, "total": 0},
}


def _today() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _load_file() -> dict:
    try:
        if STATS_FILE.exists():
            return json.loads(STATS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"[Stats] 파일 읽기 실패: {e}")
    return {"visitors": {}, "api_calls": {"daily": {}, "total": 0}}


def _save_file(visitors_dict: dict, api_calls: dict) -> None:
    try:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "visitors": {d: list(ips) for d, ips in visitors_dict.items()},
            "api_calls": api_calls,
        }
        STATS_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"[Stats] 파일 쓰기 실패 (메모리 집계는 정상): {e}")


def _init_mem_from_file() -> None:
    """서버 시작 시 파일에서 메모리로 복원."""
    data = _load_file()
    for d, ips in data.get("visitors", {}).items():
        _mem["visitors"][d] = set(ips)
    _mem["api_calls"] = data.get("api_calls", {"daily": {}, "total": 0})


# 서버 시작 시 1회 복원
_init_mem_from_file()


def record_visit(ip: str) -> None:
    """방문 IP 기록 (일별 unique)."""
    today = _today()
    daily_set = _mem["visitors"].setdefault(today, set())
    daily_set.add(ip)

    # 7일 초과분 정리
    cutoff = (datetime.now(KST) - timedelta(days=7)).strftime("%Y-%m-%d")
    _mem["visitors"] = {d: v for d, v in _mem["visitors"].items() if d >= cutoff}

    _save_file(_mem["visitors"], _mem["api_calls"])


def record_api_call() -> None:
    """브리핑 생성 횟수 증가 (전체 IP 합산)."""
    today = _today()
    _mem["api_calls"]["daily"][today] = _mem["api_calls"]["daily"].get(today, 0) + 1
    _mem["api_calls"]["total"] = _mem["api_calls"].get("total", 0) + 1

    _save_file(_mem["visitors"], _mem["api_calls"])


def get_stats() -> dict:
    """현재 통계 반환."""
    today = _today()
    today_visitors = len(_mem["visitors"].get(today, set()))
    total_visitors = sum(len(v) for v in _mem["visitors"].values())
    today_api = _mem["api_calls"]["daily"].get(today, 0)
    total_api = _mem["api_calls"].get("total", 0)
    return {
        "todayVisitors": today_visitors,
        "totalVisitors": total_visitors,
        "todayApiCalls": today_api,
        "totalApiCalls": total_api,
    }
