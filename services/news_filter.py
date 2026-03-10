import logging
import time

logger = logging.getLogger(__name__)

HIGH_PRIORITY = [
    "war", "invasion", "military", "conflict", "missile", "nuclear",
    "fed", "federal reserve", "ecb", "boj", "pboc", "central bank",
    "rate cut", "rate hike", "interest rate", "monetary policy",
    "inflation", "cpi", "pce", "deflation",
    "oil", "crude", "opec", "energy crisis",
    "sanctions", "tariff", "trade war", "embargo",
    "recession", "gdp", "unemployment", "nonfarm", "jobs report",
    "default", "debt ceiling", "fiscal",
    "geopolitical", "escalation", "ceasefire",
    "earnings", "guidance", "buyback",
    "ai ", "artificial intelligence", "semiconductor", "chip",
    "crypto", "bitcoin", "ethereum",
    "treasury", "bond", "yield",
    "dollar", "yen", "euro", "yuan", "currency",
    "crash", "selloff", "rally", "surge", "plunge",
    "stimulus", "quantitative", "tightening", "easing",
]

MEDIUM_PRIORITY = [
    "sector", "rotation", "defense", "shipping", "real estate",
    "bank", "financial", "tech", "healthcare", "pharma",
    "supply chain", "commodity", "gold", "silver", "copper",
    "ipo", "merger", "acquisition", "split",
    "regulation", "sec", "compliance",
    "outlook", "forecast", "projection", "estimate",
    "korea", "kospi", "samsung", "hyundai", "sk",
]


def filter_news(news_items: list[dict]) -> list[dict]:
    now = time.time()
    scored = []

    for item in news_items:
        text = f"{item.get('headline', '')} {item.get('summary', '')}".lower()
        score = 0.0

        for kw in HIGH_PRIORITY:
            if kw in text:
                score += 3
        for kw in MEDIUM_PRIORITY:
            if kw in text:
                score += 1

        age_hours = (now - (item.get("datetime") or 0)) / 3600
        if age_hours < 3:
            score += 5
        elif age_hours < 6:
            score += 3
        elif age_hours < 12:
            score += 1

        scored.append({**item, "_score": score})

    scored.sort(key=lambda x: x["_score"], reverse=True)
    filtered = [x for x in scored if x["_score"] > 0][:30]

    result = filtered if filtered else scored[:20]
    logger.info(f"[NewsFilter] 필터링: {len(news_items)}건 → {len(result)}건")
    return result


def format_for_llm(news_items: list[dict]) -> str:
    text = "=== TODAY'S KEY FINANCIAL & GEOPOLITICAL NEWS ===\n\n"
    for idx, item in enumerate(news_items, 1):
        dt = item.get("datetime")
        time_str = (
            __import__("datetime").datetime.utcfromtimestamp(dt).strftime("%Y-%m-%d %H:%M")
            if dt else "N/A"
        )
        text += f"[{idx}] {item.get('headline', 'No headline')}\n"
        text += f"    Source: {item.get('source', 'Unknown')} | Time: {time_str} | Category: {item.get('_category', 'general')}\n"
        summary = item.get("summary", "")
        if summary:
            if len(summary) > 200:
                summary = summary[:200] + "..."
            text += f"    Summary: {summary}\n"
        text += "\n"
    return text
