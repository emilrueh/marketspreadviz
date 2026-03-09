from typing import Literal
from pydantic import BaseModel


class PricePoint(BaseModel):
    date: str
    close: float


class PriceResponse(BaseModel):
    ticker: str
    period: str
    data: list[PricePoint]


class SpreadPoint(BaseModel):
    date: str
    growth_a: float
    growth_b: float
    growth_spread: float


class SpikeAnnotation(BaseModel):
    date: str
    value: float
    direction: Literal["up", "down"]


class SpreadResponse(BaseModel):
    pair: str
    label: str
    ticker_a: str
    ticker_b: str
    name_a: str
    name_b: str
    period: str
    window: int
    prominence: float
    data: list[SpreadPoint]
    spikes: list[SpikeAnnotation]


class AnalysisContent(BaseModel):
    single_exact_reason: str
    detailed_summary: str


class NewsArticle(BaseModel):
    title: str
    url: str
    snippet: str = ""
    date: str = ""


class SpikeNewsResponse(BaseModel):
    pair: str
    date: str
    direction: Literal["up", "down"]
    single_exact_reason: str
    detailed_summary: str
    articles: list[NewsArticle] = []
