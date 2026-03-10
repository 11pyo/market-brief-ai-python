import json
import logging
from pathlib import Path

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


def get_portfolio() -> Portfolio:
    if not PORTFOLIO_PATH.exists():
        return DEFAULT_PORTFOLIO
    try:
        data = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        return Portfolio(**data)
    except Exception as e:
        logger.warning(f"[Portfolio] 로드 실패, 기본값 사용: {e}")
        return DEFAULT_PORTFOLIO


def save_portfolio(portfolio: Portfolio) -> None:
    PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    PORTFOLIO_PATH.write_text(portfolio.model_dump_json(indent=2), encoding="utf-8")
    logger.info("[Portfolio] 저장 완료")


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
