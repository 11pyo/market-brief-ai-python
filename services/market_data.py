import asyncio
import logging
import time

import httpx
import yfinance as yf

logger = logging.getLogger(__name__)


# ===== CNN FEAR & GREED INDEX =====
# 비공식 CNN 데이터비즈 엔드포인트 (고정 URL, 사용자 입력 아님)
_CNN_FG_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
_CNN_FG_CACHE: tuple[float, dict] | None = None
_CNN_FG_CACHE_TTL = 300  # 5분

_CNN_FG_RATING_KO: dict[str, str] = {
    "Extreme Fear": "극도의 공포",
    "Fear": "공포",
    "Neutral": "중립",
    "Greed": "탐욕",
    "Extreme Greed": "극도의 탐욕",
}
_CNN_FG_COLORS: dict[str, str] = {
    "Extreme Fear": "#ef4444",
    "Fear":         "#f97316",
    "Neutral":      "#eab308",
    "Greed":        "#84cc16",
    "Extreme Greed":"#22c55e",
}


async def get_cnn_fear_greed() -> dict | None:
    """CNN Fear & Greed Index 조회. 5분 캐시. 실패 시 None 반환."""
    global _CNN_FG_CACHE
    now = time.time()
    if _CNN_FG_CACHE:
        cached_at, cached_data = _CNN_FG_CACHE
        if now - cached_at < _CNN_FG_CACHE_TTL:
            logger.debug("[FearGreed] 캐시 히트")
            return cached_data

    try:
        # [SECURE] 고정 URL 사용 - SSRF 방지 (사용자 입력 URL 미사용)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer":    "https://edition.cnn.com/markets/fear-and-greed",
            "Origin":     "https://edition.cnn.com",
            "Accept":     "application/json, text/plain, */*",
        }
        async with httpx.AsyncClient(timeout=10, headers=headers, follow_redirects=True) as client:
            resp = await client.get(_CNN_FG_URL)
            resp.raise_for_status()
            data = resp.json()

        fg = data.get("fear_and_greed", {})
        score_raw = fg.get("score")
        rating = fg.get("rating", "")

        # fear_and_greed 필드가 없거나 score가 없으면 historical 최신 항목으로 폴백
        if score_raw is None:
            historical = data.get("fear_and_greed_historical", {}).get("data", [])
            if historical:
                latest = historical[-1]
                score_raw = latest.get("y")
                rating = latest.get("rating", "")
                logger.warning("[FearGreed] fear_and_greed 없음 → historical 최신 항목 사용")

        if score_raw is None:
            logger.warning("[FearGreed] CNN 응답에 score 없음")
            return None

        score = round(float(score_raw), 1)
        result = {
            "score":          score,
            "rating":         rating,
            "rating_ko":      _CNN_FG_RATING_KO.get(rating, rating),
            "color":          _CNN_FG_COLORS.get(rating, "#eab308"),
            "previous_close": round(float(fg.get("previous_close") or 0), 1),
            "previous_1week": round(float(fg.get("previous_1_week") or 0), 1),
            "previous_1month":round(float(fg.get("previous_1_month") or 0), 1),
            "timestamp":      fg.get("timestamp", ""),
        }
        _CNN_FG_CACHE = (now, result)
        logger.info(f"[FearGreed] CNN F&G 조회 완료: {score} ({rating})")
        return result

    except Exception as e:
        logger.warning(f"[FearGreed] CNN 조회 실패: {e}")
        return None

# 표시명 → Yahoo Finance 심볼
SYMBOLS: dict[str, str] = {
    "S&P 500":            "^GSPC",
    "NASDAQ":             "^IXIC",
    "Dow Jones":          "^DJI",
    "US 10Y Yield":       "^TNX",
    "Dollar Index (DXY)": "DX-Y.NYB",
    "Crude Oil (WTI)":    "CL=F",
    "VIX":                "^VIX",
    "Gold":               "GC=F",
    "EUR/USD":            "EURUSD=X",
    "BTC/USD":            "BTC-USD",
    "KOSPI":              "^KS11",
    "USD/KRW":            "KRW=X",
}


def _fetch_snapshot_sync() -> dict:
    """동기 yfinance 호출 (run_in_executor에서 실행)."""
    tickers = yf.Tickers(" ".join(SYMBOLS.values()))
    results = {}

    for name, symbol in SYMBOLS.items():
        try:
            info = tickers.tickers[symbol].fast_info
            price = info.last_price
            prev_close = info.previous_close
            if price is None or prev_close is None:
                raise ValueError("가격 없음")
            change = price - prev_close
            change_pct = (change / prev_close) * 100
            results[name] = {
                "price": round(price, 4),
                "change": round(change, 4),
                "changePercent": round(change_pct, 4),
            }
        except Exception as e:
            logger.warning(f"[MarketData] {name} ({symbol}) 조회 실패: {e}")
            results[name] = {"price": None, "change": None, "changePercent": None}

    success = sum(1 for v in results.values() if v["price"] is not None)
    logger.info(f"[MarketData] {success}/{len(results)}개 지표 조회 완료")
    return results


async def get_snapshot() -> dict:
    """비동기 래퍼 — 30초 캐시 적용. yfinance는 동기 라이브러리이므로 executor에서 실행."""
    global _snapshot_cache
    now = time.time()
    if _snapshot_cache:
        cached_at, cached_data = _snapshot_cache
        if now - cached_at < SNAPSHOT_CACHE_TTL:
            logger.debug("[MarketData] 스냅샷 캐시 히트")
            return cached_data
    loop = asyncio.get_event_loop()
    async with asyncio.timeout(45):
        result = await loop.run_in_executor(None, _fetch_snapshot_sync)
    _snapshot_cache = (now, result)
    return result


_snapshot_cache: tuple[float, dict] | None = None
SNAPSHOT_CACHE_TTL = 30  # 30초 — 시장 개장 중 적정, yfinance 호출 50% 절감

# ===== 섹터 ETF =====
SECTOR_SYMBOLS: dict[str, str] = {
    "Technology":          "XLK",
    "Financials":          "XLF",
    "Energy":              "XLE",
    "Healthcare":          "XLV",
    "Industrials":         "XLI",
    "Cons. Discretionary": "XLY",
    "Cons. Staples":       "XLP",
    "Communication":       "XLC",
    "Materials":           "XLB",
    "Real Estate":         "XLRE",
}

_sector_cache: tuple[float, dict] | None = None
SECTOR_CACHE_TTL = 60  # 1분


def _fetch_sector_sync() -> dict:
    symbols_str = " ".join(SECTOR_SYMBOLS.values())
    tickers = yf.Tickers(symbols_str)
    results = {}
    for name, symbol in SECTOR_SYMBOLS.items():
        try:
            info = tickers.tickers[symbol].fast_info
            price = info.last_price
            prev_close = info.previous_close
            if price is None or prev_close is None:
                raise ValueError("가격 없음")
            change = price - prev_close
            change_pct = (change / prev_close) * 100
            results[name] = {
                "symbol": symbol,
                "price": round(price, 2),
                "changePercent": round(change_pct, 2),
            }
        except Exception as e:
            logger.warning(f"[MarketData] 섹터 {name} ({symbol}) 조회 실패: {e}")
    return results


async def get_sector_snapshot() -> dict:
    global _sector_cache
    now = time.time()
    if _sector_cache:
        cached_at, cached_data = _sector_cache
        if now - cached_at < SECTOR_CACHE_TTL:
            return cached_data
    loop = asyncio.get_event_loop()
    async with asyncio.timeout(45):
        result = await loop.run_in_executor(None, _fetch_sector_sync)
    _sector_cache = (now, result)
    return result

_chart_cache: dict[str, tuple[float, list]] = {}
CHART_CACHE_TTL = 60  # 1분

PERIOD_CONFIG = {
    "1d":  {"period": "1d",  "interval": "5m"},
    "5d":  {"period": "5d",  "interval": "30m"},
    "1mo": {"period": "1mo", "interval": "1d"},
}


def _fetch_chart_sync(symbol: str, period: str) -> list:
    config = PERIOD_CONFIG.get(period, PERIOD_CONFIG["1d"])
    hist = yf.Ticker(symbol).history(period=config["period"], interval=config["interval"])
    if hist.empty:
        return []
    candles = []
    seen = set()
    for dt, row in hist.iterrows():
        ts = int(dt.timestamp())
        if ts in seen:
            continue
        seen.add(ts)
        candles.append({
            "time": ts,
            "open":  round(float(row["Open"]),  4),
            "high":  round(float(row["High"]),  4),
            "low":   round(float(row["Low"]),   4),
            "close": round(float(row["Close"]), 4),
        })
    return candles


async def get_chart(name: str, period: str = "1d") -> list:
    symbol = SYMBOLS.get(name)
    if not symbol:
        return []
    cache_key = f"{symbol}:{period}"
    now = time.time()
    if cache_key in _chart_cache:
        cached_at, cached_data = _chart_cache[cache_key]
        if now - cached_at < CHART_CACHE_TTL:
            return cached_data
    loop = asyncio.get_event_loop()
    async with asyncio.timeout(30):
        candles = await loop.run_in_executor(None, _fetch_chart_sync, symbol, period)
    _chart_cache[cache_key] = (now, candles)
    return candles


def format_for_llm(snapshot: dict, fear_greed: dict | None = None) -> str:
    text = "=== CURRENT MARKET DATA ===\n"
    for name, data in snapshot.items():
        if data["price"] is not None:
            direction = "▲" if (data["change"] or 0) >= 0 else "▼"
            pct = f" ({data['changePercent']:+.2f}%)" if data["changePercent"] is not None else ""
            text += f"{name}: {data['price']:,.2f} {direction} {abs(data['change'] or 0):.2f}{pct}\n"
        else:
            text += f"{name}: N/A\n"

    if fear_greed:
        text += (
            f"\n=== CNN FEAR & GREED INDEX (Source: CNN Markets) ===\n"
            f"Score: {fear_greed['score']} / 100 — {fear_greed['rating']} ({fear_greed['rating_ko']})\n"
            f"Previous Close: {fear_greed['previous_close']} | "
            f"1 Week Ago: {fear_greed['previous_1week']} | "
            f"1 Month Ago: {fear_greed['previous_1month']}\n"
        )
    return text
