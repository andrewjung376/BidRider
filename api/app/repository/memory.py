"""메모리 저장소. 테스트와 Supabase 연동 전 로컬 개발용이다 (서버리스에서는 요청 사이에 유지되지 않는다)."""

from datetime import datetime, time
from typing import Literal

from app.koneps.models import KST, Bid
from app.repository.base import BidRecord, BidSummaryRecord, CollectRunRecord, ProfileRecord, SettingsRecord
from app.schemas import BidFilter

_MIN_DT = datetime.min.replace(tzinfo=KST)


class InMemoryBidRepository:
    def __init__(self) -> None:
        self._bids: dict[tuple[str, str], BidRecord] = {}
        self._next_id = 1
        self._settings = SettingsRecord(categories=["용역"], num_rows=10, updated_at=datetime.now(KST))
        self._runs: list[CollectRunRecord] = []
        self._profiles: dict[str, ProfileRecord] = {}
        self._feedbacks: list[dict] = []

    async def upsert_bids(self, bids: list[Bid]) -> int:
        inserted = 0
        for bid in bids:
            key = (bid.bid_ntce_no, bid.bid_ntce_ord)
            if key in self._bids:
                self._bids[key].bid = bid
            else:
                self._bids[key] = BidRecord(id=self._next_id, bid=bid)
                self._next_id += 1
                inserted += 1
        return inserted

    async def list_bids(self, filters: BidFilter, page: int, size: int) -> tuple[list[BidRecord], int]:
        records = [r for r in self._bids.values() if _matches(r.bid, filters)]
        records.sort(key=lambda r: r.bid.bid_ntce_dt or _MIN_DT, reverse=True)
        start = (page - 1) * size
        return records[start : start + size], len(records)

    async def get_bid(self, bid_id: int) -> BidRecord | None:
        return next((r for r in self._bids.values() if r.id == bid_id), None)

    async def get_settings(self) -> SettingsRecord:
        return self._settings

    async def update_settings(self, categories: list[str], num_rows: int, updated_by: str | None) -> SettingsRecord:
        self._settings = SettingsRecord(
            categories=categories, num_rows=num_rows, updated_at=datetime.now(KST), updated_by=updated_by
        )
        return self._settings

    async def create_run(
        self, trigger: Literal["cron", "manual"], categories: list[str], requested_by: str | None
    ) -> CollectRunRecord:
        run = CollectRunRecord(
            id=len(self._runs) + 1,
            trigger=trigger,
            categories=categories,
            status="running",
            started_at=datetime.now(KST),
            requested_by=requested_by,
        )
        self._runs.append(run)
        return run

    async def finish_run(
        self,
        run_id: int,
        status: Literal["success", "failed"],
        fetched_count: int,
        inserted_count: int,
        error: str | None = None,
    ) -> None:
        run = self._runs[run_id - 1]
        run.status = status
        run.fetched_count = fetched_count
        run.inserted_count = inserted_count
        run.error = error
        run.finished_at = datetime.now(KST)

    async def last_manual_run_started_at(self) -> datetime | None:
        manual = [r.started_at for r in self._runs if r.trigger == "manual"]
        return max(manual) if manual else None

    async def list_unsummarized(self, limit: int) -> list[BidRecord]:
        records = [r for r in self._bids.values() if r.summary is None]
        records.sort(key=lambda r: r.bid.bid_ntce_dt or _MIN_DT, reverse=True)
        return records[:limit]

    async def save_summary(self, bid_id: int, summary: BidSummaryRecord) -> None:
        record = await self.get_bid(bid_id)
        if record is not None:
            record.summary = summary

    async def get_profile(self, user_id: str) -> ProfileRecord | None:
        return self._profiles.get(user_id)

    async def save_profile(self, profile: ProfileRecord) -> ProfileRecord:
        self._profiles[profile.user_id] = profile
        return profile

    async def add_feedback(self, user_id: str | None, rating: int, message: str, page: str | None) -> int:
        self._feedbacks.append({"user_id": user_id, "rating": rating, "message": message, "page": page})
        return len(self._feedbacks)

    @property
    def runs(self) -> list[CollectRunRecord]:
        return self._runs

    @property
    def feedbacks(self) -> list[dict]:
        return self._feedbacks


def _matches(bid: Bid, f: BidFilter) -> bool:
    if f.category and bid.category != f.category:
        return False
    if f.q and f.q.lower() not in bid.bid_ntce_nm.lower():
        return False
    if f.institution:
        names = f"{bid.ntce_instt_nm or ''} {bid.dminstt_nm or ''}"
        if f.institution not in names:
            return False
    if f.min_price is not None and (bid.presmpt_prce is None or bid.presmpt_prce < f.min_price):
        return False
    if f.max_price is not None and (bid.presmpt_prce is None or bid.presmpt_prce > f.max_price):
        return False
    if f.closing_from or f.closing_to:
        if bid.bid_clse_dt is None:
            return False
        if f.closing_from and bid.bid_clse_dt < datetime.combine(f.closing_from, time.min, KST):
            return False
        if f.closing_to and bid.bid_clse_dt > datetime.combine(f.closing_to, time.max, KST):
            return False
    return True
