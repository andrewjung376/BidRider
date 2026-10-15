"""테스트용 가짜 공고 소스와 공고 생성 도우미."""

from datetime import datetime, timedelta

from app.koneps.client import KonepsError
from app.koneps.models import KST, Bid


def make_bid(
    i: int,
    category: str = "용역",
    *,
    name: str | None = None,
    price: int | None = 50_000_000,
    institution: str = "서울특별시",
    closing: datetime | None = None,
    raw: dict | None = None,
) -> Bid:
    posted = datetime(2026, 10, 15, 9, 0, tzinfo=KST) + timedelta(minutes=i)
    return Bid(
        bid_ntce_no=f"R26BK{i:08d}",
        bid_ntce_ord="000",
        category=category,
        bid_ntce_nm=name or f"공고 {i}",
        ntce_instt_nm=institution,
        dminstt_nm=institution,
        presmpt_prce=price,
        bid_ntce_dt=posted,
        bid_clse_dt=closing or posted + timedelta(days=7),
        bid_ntce_dtl_url=f"https://www.g2b.go.kr/{i}",
        raw=raw or {"bidNtceNo": f"R26BK{i:08d}"},
    )


class FakeSource:
    """업무 구분별로 미리 정한 공고를 돌려주는 가짜 수집 소스."""

    def __init__(self, bids_by_category: dict[str, list[Bid]] | None = None, fail: bool = False) -> None:
        self.bids_by_category = bids_by_category or {}
        self.fail = fail
        self.calls: list[tuple[str, int]] = []

    async def fetch_latest(self, category: str = "용역", num_rows: int = 10) -> list[Bid]:
        self.calls.append((category, num_rows))
        if self.fail:
            raise KonepsError("getBidPblancListInfoServc 오류 20: ACCESS DENIED")
        return self.bids_by_category.get(category, [])[:num_rows]
