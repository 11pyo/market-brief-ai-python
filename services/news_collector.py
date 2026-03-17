import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"
CATEGORIES = ["general", "forex", "crypto", "merger"]
MAX_AGE_SECONDS = 24 * 3600  # 24시간

# 개별 기업 뉴스를 별도로 수집할 핵심 종목
COMPANY_SYMBOLS = [
    "NVDA", "AAPL", "MSFT", "META", "GOOGL",
    "AMZN", "TSLA", "AMD", "INTC", "AVGO",
]


async def _fetch_category(client: httpx.AsyncClient, category: str) -> list[dict]:
    async with asyncio.timeout(15):
        resp = await client.get(
            f"{FINNHUB_BASE}/news",
            params={"category": category, "token": settings.finnhub_api_key},
        )
        resp.raise_for_status()
        items = resp.json()
        for item in items:
            item["_category"] = category
        return items


async def _fetch_company_news(client: httpx.AsyncClient, symbol: str) -> list[dict]:
    """특정 종목의 최근 24h 뉴스 수집."""
    now_utc = datetime.now(timezone.utc)
    yesterday = now_utc - timedelta(days=1)
    try:
        async with asyncio.timeout(15):
            resp = await client.get(
                f"{FINNHUB_BASE}/company-news",
                params={
                    "symbol": symbol,
                    "from": yesterday.strftime("%Y-%m-%d"),
                    "to": now_utc.strftime("%Y-%m-%d"),
                    "token": settings.finnhub_api_key,
                },
            )
            resp.raise_for_status()
            items = resp.json()
            if not isinstance(items, list):
                return []
            for item in items:
                item["_category"] = "company"
                item["_symbol"] = symbol
            return items
    except Exception as e:
        logger.warning(f"[NewsCollector] {symbol} 기업 뉴스 실패: {e}")
        return []


async def collect_all() -> list[dict[str, Any]]:
    """카테고리 뉴스 + 핵심 종목 기업 뉴스를 병렬 수집 후 24h 필터 + 중복 제거."""
    async with httpx.AsyncClient(timeout=20) as client:
        category_tasks = [_fetch_category(client, cat) for cat in CATEGORIES]
        company_tasks = [_fetch_company_news(client, sym) for sym in COMPANY_SYMBOLS]

        all_results = await asyncio.gather(
            *category_tasks, *company_tasks,
            return_exceptions=True,
        )

    now = time.time()
    all_items: list[dict] = []

    for i, result in enumerate(all_results):
        if isinstance(result, Exception):
            label = CATEGORIES[i] if i < len(CATEGORIES) else COMPANY_SYMBOLS[i - len(CATEGORIES)]
            logger.warning(f"[NewsCollector] {label} 수집 실패: {result}")
            continue
        all_items.extend(result)

    # 24시간 이내만 유지
    fresh = [item for item in all_items if now - (item.get("datetime") or 0) <= MAX_AGE_SECONDS]

    # 중복 제거 (id 기준, 없으면 headline 기준)
    seen: set = set()
    unique: list[dict] = []
    for item in fresh:
        key = item.get("id") or item.get("headline", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(item)

    logger.info(
        f"[NewsCollector] 수집: {len(all_items)}건 → 24h 필터 후 {len(unique)}건 "
        f"(카테고리 {len(CATEGORIES)}개 + 종목 {len(COMPANY_SYMBOLS)}개)"
    )
    return unique[:120]
