import asyncio
import logging
from functools import partial

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
    """비동기 래퍼 — yfinance는 동기 라이브러리이므로 executor에서 실행."""
    loop = asyncio.get_event_loop()
    async with asyncio.timeout(45):
        return await loop.run_in_executor(None, _fetch_snapshot_sync)


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
