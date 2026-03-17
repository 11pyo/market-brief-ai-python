"""
경제지표 캘린더 + 어닝(실적 발표) 캘린더.
- Finnhub /api/v1/calendar/economic
- Finnhub /api/v1/calendar/earnings
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

import httpx

from config import settings

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"

# 관심 종목 실적 발표 우선 표시
MAJOR_SYMBOLS = {
    "NVDA", "AAPL", "MSFT", "META", "GOOGL", "AMZN", "TSLA", "AMD",
    "INTC", "AVGO", "TSM", "QCOM", "MU", "NFLX", "CRM", "JPM", "GS",
    "BAC", "V", "MA", "PYPL", "COIN", "PLTR",
}


async def _fetch(client: httpx.AsyncClient, url: str, params: dict) -> dict | list | None:
    try:
        async with asyncio.timeout(10):
            params["token"] = settings.finnhub_api_key
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"[Calendar] 요청 실패 {url}: {e}")
        return None


async def get_economic_events(days: int = 5) -> list[dict]:
    """당일부터 N일간의 고영향 경제지표 일정."""
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)
    params = {
        "from": now.strftime("%Y-%m-%d"),
        "to": end.strftime("%Y-%m-%d"),
    }
    async with httpx.AsyncClient(timeout=15) as client:
        data = await _fetch(client, f"{FINNHUB_BASE}/calendar/economic", params)

    if not data or "economicCalendar" not in data:
        return []

    events = []
    for ev in data["economicCalendar"]:
        impact = (ev.get("impact") or "").lower()
        country = (ev.get("country") or "").upper()
        # 고영향 지표 또는 미국 중영향 이상만
        if country not in ("US", "EU", "CN", "JP", "KR"):
            continue
        if impact not in ("high", "medium") and country != "US":
            continue
        events.append({
            "event": ev.get("event", ""),
            "time": ev.get("time", ""),
            "country": country,
            "impact": impact,
            "estimate": ev.get("estimate"),
            "prev": ev.get("prev"),
            "actual": ev.get("actual"),
            "unit": ev.get("unit", ""),
        })

    # 날짜순 정렬, 고영향 우선
    impact_order = {"high": 0, "medium": 1, "low": 2}
    events.sort(key=lambda x: (x.get("time", ""), impact_order.get(x.get("impact", "low"), 2)))
    return events[:30]


async def get_earnings_events(days: int = 7) -> list[dict]:
    """당일부터 N일간의 주요 기업 실적 발표 일정."""
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)
    params = {
        "from": now.strftime("%Y-%m-%d"),
        "to": end.strftime("%Y-%m-%d"),
    }
    async with httpx.AsyncClient(timeout=15) as client:
        data = await _fetch(client, f"{FINNHUB_BASE}/calendar/earnings", params)

    if not data or "earningsCalendar" not in data:
        return []

    events = []
    for ev in data["earningsCalendar"]:
        symbol = (ev.get("symbol") or "").upper()
        is_major = symbol in MAJOR_SYMBOLS
        events.append({
            "symbol": symbol,
            "company": ev.get("company", symbol),
            "date": ev.get("date", ""),
            "hour": ev.get("hour", ""),      # bmo=장전, amc=장후
            "epsEstimate": ev.get("epsEstimate"),
            "revenueEstimate": ev.get("revenueEstimate"),
            "isMajor": is_major,
        })

    # 주요 종목 먼저, 그 다음 날짜순
    events.sort(key=lambda x: (x["date"], 0 if x["isMajor"] else 1))
    # 주요 종목은 모두 포함, 나머지는 25개까지
    major = [e for e in events if e["isMajor"]]
    others = [e for e in events if not e["isMajor"]]
    return (major + others[:max(0, 25 - len(major))])[:30]


async def get_calendar(days_eco: int = 5, days_earn: int = 7) -> dict:
    eco, earn = await asyncio.gather(
        get_economic_events(days_eco),
        get_earnings_events(days_earn),
    )
    return {"economic": eco, "earnings": earn}
