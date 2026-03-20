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
    # 대통령·정치 발표
    "trump", "president", "white house", "executive order", "oval office",
    "powell", "fed chair", "yellen", "waller", "goolsbee", "bessent",
    "press conference", "press secretary",
    # 관세·무역 정책
    "trade deal", "export control", "import ban", "import tariff",
    "retaliatory", "reciprocal tariff",
    # 핵심 기업 (개별 종목 뉴스 포착)
    "nvidia", "nvda", "jensen huang",
    "apple", "aapl", "tim cook",
    "microsoft", "msft", "satya nadella",
    "meta platforms", "meta ai", "zuckerberg",
    "alphabet", "google", "sundar pichai",
    "amazon", "aws", "andy jassy",
    "tesla", "elon musk",
    "amd", "intel", "broadcom", "qualcomm",
    # 기업 이벤트
    "product launch", "announced", "unveil", "revenue beat", "revenue miss",
    "outlook raised", "outlook cut", "layoff", "restructur",
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

# 권위 있는 출처 → 가산점 (소문자 부분 일치)
AUTHORITATIVE_SOURCES: dict[str, float] = {
    # Tier 1 — 글로벌 1급 미디어 (+5점)
    "reuters":              5,
    "bloomberg":            5,
    "financial times":      5,
    "ft.com":               5,
    "wall street journal":  5,
    "wsj":                  5,
    "associated press":     5,
    "ap news":              5,
    "afp":                  4,
    "cnn":                  4,   # CNN Business / CNN Markets
    # Tier 2 — 신뢰도 높은 경제·금융 미디어 (+3점)
    "cnbc":                 3,
    "bbc":                  3,
    "the economist":        3,
    "barron":               3,
    "marketwatch":          3,
    "nikkei":               3,
    "south china morning":  3,
    "handelsbla":           3,  # Handelsblatt
    # Tier 3 — 전문 금융 미디어 (+2점)
    "fortune":              2,
    "business insider":     2,
    "investing.com":        2,
    "seeking alpha":        2,
    "yahoo finance":        2,
    "benzinga":             2,
    "thestreet":            2,
    "motley fool":          1,
}

# 카테고리별 최소 보장 건수 (총합 = TOTAL_LIMIT 이하)
CATEGORY_QUOTA: dict[str, int] = {
    "general": 12,   # 매크로·지정학·경제 지표
    "forex":    5,   # 환율·통화
    "crypto":   4,   # 암호화폐
    "merger":   4,   # M&A·기업 이벤트
    "company": 10,   # 핵심 종목 기업 뉴스 (NVDA, AAPL 등)
}
TOTAL_LIMIT = 35


def _source_bonus(source: str) -> float:
    """출처명에 따라 권위 점수 반환."""
    src = source.lower()
    for keyword, bonus in AUTHORITATIVE_SOURCES.items():
        if keyword in src:
            return bonus
    return 0.0


def _score_item(item: dict, now: float) -> dict:
    """단일 뉴스 아이템에 점수 부여."""
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

    score += _source_bonus(item.get("source", ""))

    return {**item, "_score": score}


def filter_news(news_items: list[dict]) -> list[dict]:
    now = time.time()

    # 1단계: 전체 점수 계산
    scored = [_score_item(item, now) for item in news_items]
    scored.sort(key=lambda x: x["_score"], reverse=True)

    # 2단계: 카테고리별 쿼터로 다양성 확보
    buckets: dict[str, list[dict]] = {cat: [] for cat in CATEGORY_QUOTA}
    remainder: list[dict] = []

    for item in scored:
        cat = item.get("_category", "general")
        quota = CATEGORY_QUOTA.get(cat, 0)
        if cat in buckets and len(buckets[cat]) < quota:
            buckets[cat].append(item)
        else:
            remainder.append(item)

    # 3단계: 쿼터 채운 뒤 남은 슬롯을 전체 상위 점수로 채움
    selected: list[dict] = []
    for items in buckets.values():
        selected.extend(items)

    selected_ids = {id(x) for x in selected}
    for item in remainder:
        if len(selected) >= TOTAL_LIMIT:
            break
        if id(item) not in selected_ids:
            selected.append(item)

    # 4단계: 점수 0 이하인 항목 제거 (단, 최소 20건은 보장)
    valid = [x for x in selected if x["_score"] > 0]
    result = valid if len(valid) >= 20 else selected[:20]

    # 최종 점수 내림차순 정렬
    result.sort(key=lambda x: x["_score"], reverse=True)
    result = result[:TOTAL_LIMIT]

    tier1 = sum(1 for x in result if _source_bonus(x.get("source", "")) >= 5)
    tier2 = sum(1 for x in result if 2 <= _source_bonus(x.get("source", "")) < 5)
    cats = {x.get("_category", "?") for x in result}
    logger.info(
        f"[NewsFilter] {len(news_items)}건 → {len(result)}건 "
        f"(Tier1 출처: {tier1}건, Tier2: {tier2}건, 카테고리: {cats})"
    )
    return result


def format_for_llm(news_items: list[dict]) -> str:
    import datetime as _dt
    now = time.time()

    # ⚡ BREAKING 섹션: 12h 이내 + 점수 4점 이상 + 매크로·기업·환율 카테고리
    BREAKING_CATEGORIES = {"general", "forex", "company"}
    breaking = [
        x for x in news_items
        if (now - (x.get("datetime") or 0)) < 12 * 3600
        and x.get("_score", 0) >= 4
        and x.get("_category", "general") in BREAKING_CATEGORIES
    ]
    breaking.sort(key=lambda x: x["_score"], reverse=True)
    breaking = breaking[:5]

    text = ""
    if breaking:
        text += "⚡ BREAKING: HIGH-IMPACT OVERNIGHT DEVELOPMENTS (last 12h)\n"
        text += (
            "*** CRITICAL INSTRUCTION TO LLM ***\n"
            "These are the most important recent events. PART 1 MUST open by naming the specific person/company "
            "and their exact action. Do NOT write vague summaries. Prioritize ANY presidential announcement, "
            "major company earnings/product launch, or Fed statement listed here.\n\n"
        )
        for item in breaking:
            dt = item.get("datetime")
            time_str = (
                _dt.datetime.utcfromtimestamp(dt).strftime("%H:%M UTC")
                if dt else "N/A"
            )
            sym = f" [{item['_symbol']}]" if item.get("_symbol") else ""
            text += f"▶ [{time_str}]{sym} {item.get('headline', '')}\n"
            summary = item.get("summary", "")
            if summary:
                text += f"   {summary[:250]}\n"
        text += "\n---\n\n"

    text += "=== TODAY'S KEY FINANCIAL & GEOPOLITICAL NEWS ===\n\n"
    for idx, item in enumerate(news_items, 1):
        dt = item.get("datetime")
        time_str = (
            _dt.datetime.utcfromtimestamp(dt).strftime("%Y-%m-%d %H:%M")
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
