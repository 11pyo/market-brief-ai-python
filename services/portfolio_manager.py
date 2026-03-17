import json
import logging
import re
from pathlib import Path

import httpx

from config import settings
from schemas import Portfolio, PortfolioAllocation

logger = logging.getLogger(__name__)

PORTFOLIO_PATH = Path("data/portfolio.json")

DEFAULT_PORTFOLIO = Portfolio(
    allocations=[
        PortfolioAllocation(name="주식 (Equities)", percentage=60, details="미국 대형주 중심"),
        PortfolioAllocation(name="테크 (Technology)", percentage=20, details="반도체, AI, 클라우드"),
        PortfolioAllocation(name="암호화폐 (Crypto)", percentage=10, details="BTC, ETH"),
        PortfolioAllocation(name="현금 (Cash)", percentage=10, details="USD, KRW"),
    ],
    investmentStyle="Growth",
    riskTolerance="Medium-High",
    totalAssets="",
    watchlist=["NVDA", "AAPL", "TSLA", "SPY", "QQQ", "BTC-USD"],
)

_CLIENT_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{8,64}$')


def _redis_enabled() -> bool:
    return bool(settings.upstash_redis_url and settings.upstash_redis_token)


def _valid_client_id(client_id: str) -> bool:
    return bool(client_id and _CLIENT_ID_RE.match(client_id))


async def _redis_pipeline(commands: list) -> list:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{settings.upstash_redis_url}/pipeline",
                headers={"Authorization": f"Bearer {settings.upstash_redis_token}"},
                json=commands,
            )
            body = r.json()
            if not isinstance(body, list):
                logger.warning(f"[Portfolio] Redis 비정상 응답: {body}")
                return []
            return [item.get("result") if isinstance(item, dict) else None for item in body]
    except Exception as e:
        logger.warning(f"[Portfolio] Redis 호출 실패: {e}")
        return []


async def get_portfolio(client_id: str = "") -> Portfolio:
    """client_id가 있으면 Redis에서, 없으면 로컬 파일에서 로드."""
    if _valid_client_id(client_id) and _redis_enabled():
        results = await _redis_pipeline([["GET", f"portfolio:{client_id}"]])
        if results and results[0]:
            try:
                return Portfolio(**json.loads(results[0]))
            except Exception as e:
                logger.warning(f"[Portfolio] Redis 파싱 실패: {e}")

    # 로컬 파일 fallback (개발환경 / Redis 미설정)
    if not PORTFOLIO_PATH.exists():
        return DEFAULT_PORTFOLIO
    try:
        data = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        return Portfolio(**data)
    except Exception as e:
        logger.warning(f"[Portfolio] 로드 실패, 기본값 사용: {e}")
        return DEFAULT_PORTFOLIO


async def save_portfolio(portfolio: Portfolio, client_id: str = "") -> None:
    """client_id가 있으면 Redis에, 없으면 로컬 파일에 저장."""
    if _valid_client_id(client_id) and _redis_enabled():
        await _redis_pipeline([["SET", f"portfolio:{client_id}", portfolio.model_dump_json()]])
        logger.info(f"[Portfolio] Redis 저장 완료 (client: {client_id[:8]}...)")
        return

    # 로컬 파일 fallback
    PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    PORTFOLIO_PATH.write_text(portfolio.model_dump_json(indent=2), encoding="utf-8")
    logger.info("[Portfolio] 파일 저장 완료")


def format_for_llm(portfolio: Portfolio) -> str:
    if not portfolio.allocations:
        return ""
    lines = [
        f"Investment Style: {portfolio.investmentStyle}",
        f"Risk Tolerance: {portfolio.riskTolerance}",
        f"Total Assets: {portfolio.totalAssets or 'Not specified'}",
        "",
        "Asset Allocation:",
    ]
    for alloc in portfolio.allocations:
        line = f"- {alloc.name}: {alloc.percentage}%"
        if alloc.details:
            line += f" ({alloc.details})"
        lines.append(line)
    if portfolio.watchlist:
        lines.append(f"\nWatchlist: {', '.join(portfolio.watchlist)}")
    return "\n".join(lines)
