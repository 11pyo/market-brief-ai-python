from pydantic import BaseModel
from typing import Optional, Any


class MarketInfo(BaseModel):
    price: Optional[float] = None
    change: Optional[float] = None
    changePercent: Optional[float] = None


class BriefingRecord(BaseModel):
    id: str
    date: str
    generatedAt: str          # ISO 8601 문자열
    content: str              # 마크다운 텍스트
    model: str
    newsCount: int
    generationTimeMs: Optional[int] = None
    preview: Optional[str] = None


class PortfolioAllocation(BaseModel):
    name: str
    percentage: int
    details: str = ""


class Portfolio(BaseModel):
    allocations: list[PortfolioAllocation] = []
    investmentStyle: str = "Growth"
    riskTolerance: str = "Medium-High"
    totalAssets: str = ""
    watchlist: list[str] = []


class ApiResponse(BaseModel):
    data: Any = None
    message: str = "ok"
