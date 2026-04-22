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


class TopicCoverage(BaseModel):
    topic_id: str
    topic_name: str
    visibility: float = 0.0


class DomainSource(BaseModel):
    domain: str
    classification: str | None = None
    retrieved_percentage: float = 0.0
    mentioned_brand_ids: list[str] = Field(default_factory=list)


class PeecData(BaseModel):
    project_id: str
    own_brand: Brand
    competitors: list[Brand] = Field(default_factory=list)
    topics: list[TopicCoverage] = Field(default_factory=list)
    domain_sources: list[DomainSource] = Field(default_factory=list)
    gap_sources: list[DomainSource] = Field(default_factory=list)
    total_chats: int = 0
    date_range: tuple[str, str]


class TabularResponse(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int | None = Field(default=None, alias="rowCount")
