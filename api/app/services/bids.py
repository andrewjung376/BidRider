"""공고 도구의 실제 로직 (PRD 5.2).

API 라우터, Bid Agent(LLM tool calling), FastMCP가 모두 이 함수들을 호출한다.
"""

from datetime import datetime
from typing import Literal, Protocol

from app.koneps.client import KonepsError
from app.koneps.models import KST, Bid
from app.repository.base import BidRecord, BidRepository
from app.schemas import (
    Attachment,
    BidDetailOut,
    BidFilter,
    BidListOut,
    BidOut,
    BidSummaryOut,
    CollectOut,
    SettingsOut,
)

MANUAL_COLLECT_INTERVAL_SECONDS = 60


class BidSource(Protocol):
    async def fetch_latest(self, category: str = "용역", num_rows: int = 10) -> list[Bid]: ...


class CollectRateLimited(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__(f"{retry_after}초 후에 다시 수집할 수 있습니다.")
        self.retry_after = retry_after


class CollectFailed(Exception):
    def __init__(self, run_id: int, message: str) -> None:
        super().__init__(message)
        self.run_id = run_id


async def collect_latest(
    repo: BidRepository,
    source: BidSource,
    *,
    trigger: Literal["cron", "manual"],
    categories: list[str] | None = None,
    num_rows: int | None = None,
    requested_by: str | None = None,
    now: datetime | None = None,
) -> CollectOut:
    """업무 구분별 최신 공고를 수집해 저장한다. 값을 생략하면 저장된 수집 설정을 따른다."""
    if trigger == "manual":
        last = await repo.last_manual_run_started_at()
        elapsed = ((now or datetime.now(KST)) - last).total_seconds() if last else None
        if elapsed is not None and elapsed < MANUAL_COLLECT_INTERVAL_SECONDS:
            raise CollectRateLimited(max(1, int(MANUAL_COLLECT_INTERVAL_SECONDS - elapsed)))

    settings = await repo.get_settings()
    targets = list(dict.fromkeys(categories or settings.categories))
    rows = num_rows or settings.num_rows

    run = await repo.create_run(trigger, targets, requested_by)
    fetched: list[Bid] = []
    try:
        for category in targets:
            fetched.extend(await source.fetch_latest(category, rows))
    except KonepsError as exc:
        await repo.finish_run(run.id, "failed", len(fetched), 0, str(exc))
        raise CollectFailed(run.id, str(exc)) from None

    inserted = await repo.upsert_bids(fetched)
    await repo.finish_run(run.id, "success", len(fetched), inserted)
    return CollectOut(
        run_id=run.id, status="success", categories=targets, fetched_count=len(fetched), inserted_count=inserted
    )


async def search_bids(repo: BidRepository, filters: BidFilter, page: int = 1, size: int = 20) -> BidListOut:
    records, total = await repo.list_bids(filters, page, size)
    return BidListOut(items=[to_bid_out(r) for r in records], total=total, page=page, size=size)


async def get_bid_detail(repo: BidRepository, bid_id: int) -> BidDetailOut | None:
    record = await repo.get_bid(bid_id)
    if record is None:
        return None
    return BidDetailOut(**to_bid_out(record).model_dump(), attachments=_attachments(record.bid.raw))


async def get_settings(repo: BidRepository) -> SettingsOut:
    s = await repo.get_settings()
    return SettingsOut(categories=s.categories, num_rows=s.num_rows, updated_at=s.updated_at)


async def update_settings(
    repo: BidRepository, categories: list[str], num_rows: int, updated_by: str | None
) -> SettingsOut:
    s = await repo.update_settings(categories, num_rows, updated_by)
    return SettingsOut(categories=s.categories, num_rows=s.num_rows, updated_at=s.updated_at)


def to_bid_out(record: BidRecord) -> BidOut:
    bid = record.bid
    summary = None
    if record.summary:
        summary = BidSummaryOut(
            summary=record.summary.summary,
            qualifications=record.summary.qualifications,
            required_documents=record.summary.required_documents,
            model=record.summary.model,
        )
    return BidOut(
        id=record.id,
        summary=summary,
        **bid.model_dump(exclude={"raw"}),
    )


def _attachments(raw: dict) -> list[Attachment]:
    attachments = []
    for i in range(1, 11):
        url, name = raw.get(f"ntceSpecDocUrl{i}"), raw.get(f"ntceSpecFileNm{i}")
        if url:
            attachments.append(Attachment(name=name or f"첨부파일 {i}", url=url))
    return attachments
