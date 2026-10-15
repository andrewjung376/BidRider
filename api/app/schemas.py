"""API 요청·응답 모델. 형식은 doc/data-contract.md 3장을 따른다."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Category = Literal["용역", "공사", "물품", "외자"]


class BidSummaryOut(BaseModel):
    summary: str
    qualifications: str | None = None
    required_documents: list[str] = []
    ai_generated: bool = True
    model: str


class BidOut(BaseModel):
    id: int
    bid_ntce_no: str
    bid_ntce_ord: str
    category: Category
    bid_ntce_nm: str
    ntce_instt_nm: str | None = None
    dminstt_nm: str | None = None
    presmpt_prce: int | None = None
    bid_ntce_dt: datetime | None = None
    bid_clse_dt: datetime | None = None
    openg_dt: datetime | None = None
    bid_ntce_dtl_url: str | None = None
    summary: BidSummaryOut | None = None


class Attachment(BaseModel):
    name: str
    url: str


class BidDetailOut(BidOut):
    attachments: list[Attachment] = []


class BidListOut(BaseModel):
    items: list[BidOut]
    total: int
    page: int
    size: int


class BidFilter(BaseModel):
    category: Category | None = None
    q: str | None = None
    institution: str | None = None
    min_price: int | None = None
    max_price: int | None = None
    closing_from: date | None = None
    closing_to: date | None = None


class CollectIn(BaseModel):
    categories: list[Category] | None = Field(default=None, min_length=1)
    num_rows: int | None = Field(default=None, ge=1, le=100)


class CollectOut(BaseModel):
    run_id: int
    status: Literal["success", "failed"]
    categories: list[Category]
    fetched_count: int
    inserted_count: int


class SettingsIn(BaseModel):
    categories: list[Category] = Field(min_length=1)
    num_rows: int = Field(ge=1, le=100)

    @field_validator("categories")
    @classmethod
    def _dedupe(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class SettingsOut(BaseModel):
    categories: list[Category]
    num_rows: int
    updated_at: datetime
