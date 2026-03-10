import asyncio
import logging
import time
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"
CATEGORIES = ["general", "forex", "crypto", "merger"]
MAX_AGE_SECONDS = 24 * 3600  # 24시간


async def _fetch_category(client: httpx.AsyncClient, category: str) -> list[dict]:
    async with asyncio.timeout(15):
        resp = await client.get(
            f"{FINNHUB_BASE}/news",
            params={"category": category, "token": settings.finnhub_api_key},
        )
        resp.raise_for_status()
        items = resp.json()
        # 카테고리 태그 추가
        for item in items:
            item["_category"] = category
        return items


async def collect_all() -> list[dict[str, Any]]:
    """모든 카테고리 뉴스를 병렬 수집 후 24h 필터 + 중복 제거."""
    async with httpx.AsyncClient(timeout=20) as client:
        results = await asyncio.gather(
            *[_fetch_category(client, cat) for cat in CATEGORIES],
            return_exceptions=True,
        )

    now = time.time()
    all_items: list[dict] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"[NewsCollector] {CATEGORIES[i]} 카테고리 실패: {result}")
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

    logger.info(f"[NewsCollector] 수집: {len(all_items)}건 → 24h 필터 후 {len(unique)}건")
    return unique[:50]
