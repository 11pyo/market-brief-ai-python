import asyncio
import logging
import time

import yfinance as yf

logger = logging.getLogger(__name__)

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


def format_for_llm(snapshot: dict) -> str:
    text = "=== CURRENT MARKET DATA ===\n"
    for name, data in snapshot.items():
        if data["price"] is not None:
            direction = "▲" if (data["change"] or 0) >= 0 else "▼"
            pct = f" ({data['changePercent']:+.2f}%)" if data["changePercent"] is not None else ""
            text += f"{name}: {data['price']:,.2f} {direction} {abs(data['change'] or 0):.2f}{pct}\n"
        else:
            text += f"{name}: N/A\n"
    return text
