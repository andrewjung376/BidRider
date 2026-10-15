"""입찰공고 응답 모델. 서비스에서 쓰는 필드만 꺼내고 원본은 raw에 보관한다."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_int(value: str | int | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


class Bid(BaseModel):
    bid_ntce_no: str  # 공고번호
    bid_ntce_ord: str  # 차수
    category: str  # 업무 구분 (용역/공사/물품/외자)
    bid_ntce_nm: str  # 공고명
    ntce_instt_nm: str | None = None  # 공고기관
    dminstt_nm: str | None = None  # 수요기관
    presmpt_prce: int | None = None  # 추정가격
    bid_ntce_dt: datetime | None = None  # 공고게시일시
    bid_clse_dt: datetime | None = None  # 입찰마감일시
    openg_dt: datetime | None = None  # 개찰일시
    bid_ntce_dtl_url: str | None = None  # 상세 URL
    raw: dict[str, Any]

    @classmethod
    def from_item(cls, item: dict[str, Any], category: str) -> "Bid":
        return cls(
            bid_ntce_no=item["bidNtceNo"],
            bid_ntce_ord=item.get("bidNtceOrd") or "000",
            category=category,
            bid_ntce_nm=item.get("bidNtceNm") or "",
            ntce_instt_nm=item.get("ntceInsttNm"),
            dminstt_nm=item.get("dminsttNm"),
            presmpt_prce=_parse_int(item.get("presmptPrce")),
            bid_ntce_dt=_parse_dt(item.get("bidNtceDt")),
            bid_clse_dt=_parse_dt(item.get("bidClseDt")),
            openg_dt=_parse_dt(item.get("opengDt")),
            bid_ntce_dtl_url=item.get("bidNtceDtlUrl"),
            raw=item,
        )
