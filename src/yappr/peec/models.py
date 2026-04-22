from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Project(BaseModel):
    id: str
    name: str


class Brand(BaseModel):
    id: str
    name: str
    domains: list[str] = Field(default_factory=list)
    is_own: bool = False
    visibility: float = 0.0
    sentiment: float = 0.0
    position: float = 0.0
    share_of_voice: float = 0.0
    mention_count: int = 0
    visibility_count: int = 0
    visibility_total: int = 0


class Topic(BaseModel):
    id: str
    name: str


class AIModel(BaseModel):
    id: str
    name: str
    is_active: bool = False


class TopicCoverage(BaseModel):
    topic_id: str
    topic_name: str
    visibility: float = 0.0
    competitor_max_visibility: float = 0.0
    top_competitor_name: str | None = None


class DomainSource(BaseModel):
    domain: str
    classification: str | None = None
    retrieved_percentage: float = 0.0
    retrieval_rate: float = 0.0
    citation_rate: float = 0.0
    mentioned_brand_ids: list[str] = Field(default_factory=list)


class URLSource(BaseModel):
    url: str
    classification: str | None = None
    title: str | None = None
    channel_title: str | None = None
    retrievals: int = 0
    citation_count: int = 0
    citation_rate: float = 0.0
    mentioned_brand_ids: list[str] = Field(default_factory=list)


class PeecData(BaseModel):
    project_id: str
    project_name: str | None = None
    project_scope: str
    domain: str
    own_brand: Brand
    competitors: list[Brand] = Field(default_factory=list)
    topics: list[TopicCoverage] = Field(default_factory=list)
    all_domain_sources: list[DomainSource] = Field(default_factory=list)
    domain_sources: list[DomainSource] = Field(default_factory=list)
    gap_sources: list[DomainSource] = Field(default_factory=list)
    gap_url_sources: list[URLSource] = Field(default_factory=list)
    active_models: list[str] = Field(default_factory=list)
    total_chats: int = 0
    date_range: tuple[str, str]


class Opportunity(BaseModel):
    id: str
    category: str
    label: str
    impact: int


class AuditReport(BaseModel):
    domain: str
    project_name: str | None = None
    project_scope: str
    date_range: tuple[str, str]
    models: list[str] = Field(default_factory=list)
    score: int
    symbol: str
    color: str
    label: str
    checks: list[Any] = Field(default_factory=list)
    opportunities: list[Opportunity] = Field(default_factory=list)


class TabularResponse(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int | None = Field(default=None, alias="rowCount")
