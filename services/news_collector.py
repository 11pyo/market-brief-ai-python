import asyncio
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"
CATEGORIES = ["general", "forex", "crypto", "merger"]
MAX_AGE_SECONDS = 24 * 3600  # 24시간

# ===== 직접 RSS 피드 (Reuters, CNN) =====
# [SECURE] 고정 URL만 사용 - SSRF 방지 (사용자 입력 URL 미사용)
RSS_FEEDS: list[tuple[str, str]] = [
    ("Reuters Business",  "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Top News",  "https://feeds.reuters.com/reuters/topNews"),
    ("CNN Business",      "https://rss.cnn.com/rss/money_news_international.rss"),
]
RSS_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MarketBriefBot/1.0)"}

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


def _parse_rss_date(date_str: str | None) -> int | None:
    """RFC 2822 날짜 문자열 → Unix timestamp. 실패 시 None."""
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        return int(dt.timestamp())
    except Exception:
        return None


def _strip_html(text: str) -> str:
    """단순 HTML 태그 제거 (ElementTree 파싱 없이 정규식 미사용)."""
    import re
    # [SECURE] 정규식으로 HTML 태그 제거 - XSS 방지용 출력 정제
    clean = re.sub(r"<[^>]+>", " ", text)
    return " ".join(clean.split())


async def _fetch_rss(client: httpx.AsyncClient, source_name: str, url: str) -> list[dict]:
    """RSS 피드 파싱 → Finnhub 호환 형식 변환."""
    try:
        async with asyncio.timeout(15):
            resp = await client.get(url, headers=RSS_HEADERS)
            resp.raise_for_status()
            content = resp.text

        root = ET.fromstring(content)
        # RSS 2.0: rss/channel/item  또는 Atom 네임스페이스 고려
        ns_strip = lambda tag: tag.split("}")[-1] if "}" in tag else tag

        items_el = root.findall(".//item")
        results: list[dict] = []
        for item in items_el[:30]:  # 피드당 최대 30건
            def txt(tag: str) -> str:
                el = item.find(tag)
                return (el.text or "").strip() if el is not None else ""

            headline = _strip_html(txt("title"))
            summary  = _strip_html(txt("description"))
            pub_date = txt("pubDate") or txt("pubdate")
            link     = txt("link")
            ts       = _parse_rss_date(pub_date)

            if not headline:
                continue

            results.append({
                "id":        link or headline,
                "headline":  headline,
                "summary":   summary[:300] if summary else "",
                "datetime":  ts,
                "source":    source_name,
                "url":       link,
                "_category": "general",
                "_rss":      True,
            })

        logger.info(f"[RSS] {source_name}: {len(results)}건 수집")
        return results

    except Exception as e:
        logger.warning(f"[RSS] {source_name} 수집 실패: {e}")
        return []


async def collect_all() -> list[dict[str, Any]]:
    """Finnhub(카테고리+기업) + Reuters/CNN RSS를 병렬 수집 후 24h 필터 + 중복 제거."""
    async with httpx.AsyncClient(timeout=20) as client:
        category_tasks = [_fetch_category(client, cat) for cat in CATEGORIES]
        company_tasks  = [_fetch_company_news(client, sym) for sym in COMPANY_SYMBOLS]
        rss_tasks      = [_fetch_rss(client, name, url) for name, url in RSS_FEEDS]

        all_results = await asyncio.gather(
            *category_tasks, *company_tasks, *rss_tasks,
            return_exceptions=True,
        )

    now = time.time()
    all_items: list[dict] = []
    n_finnhub = len(CATEGORIES) + len(COMPANY_SYMBOLS)

    for i, result in enumerate(all_results):
        if isinstance(result, Exception):
            if i < len(CATEGORIES):
                label = CATEGORIES[i]
            elif i < n_finnhub:
                label = COMPANY_SYMBOLS[i - len(CATEGORIES)]
            else:
                label = RSS_FEEDS[i - n_finnhub][0]
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

    rss_count = sum(1 for x in unique if x.get("_rss"))
    logger.info(
        f"[NewsCollector] 수집: {len(all_items)}건 → 24h 필터 후 {len(unique)}건 "
        f"(Finnhub: {len(unique)-rss_count}건, RSS: {rss_count}건)"
    )
    return unique[:150]
