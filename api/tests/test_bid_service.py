from datetime import date, datetime, timedelta

import pytest

from app.koneps.models import KST
from app.repository import InMemoryBidRepository
from app.schemas import BidFilter
from app.services import bids as service
from app.services.bids import CollectFailed, CollectRateLimited
from tests.fakes import FakeSource, make_bid


@pytest.mark.anyio
async def test_collect_uses_saved_settings_and_dedupes() -> None:
    repo = InMemoryBidRepository()
    source = FakeSource({"용역": [make_bid(i) for i in range(12)]})

    first = await service.collect_latest(repo, source, trigger="cron")
    second = await service.collect_latest(repo, source, trigger="cron")

    assert source.calls == [("용역", 10), ("용역", 10)]
    assert (first.fetched_count, first.inserted_count) == (10, 10)
    assert (second.fetched_count, second.inserted_count) == (10, 0)  # 같은 (공고번호, 차수)는 덮어쓰기
    assert [r.status for r in repo.runs] == ["success", "success"]


@pytest.mark.anyio
async def test_collect_with_explicit_categories() -> None:
    repo = InMemoryBidRepository()
    source = FakeSource({"용역": [make_bid(1)], "공사": [make_bid(2, "공사")]})

    result = await service.collect_latest(repo, source, trigger="cron", categories=["공사", "용역", "공사"], num_rows=5)

    assert result.categories == ["공사", "용역"]
    assert source.calls == [("공사", 5), ("용역", 5)]
    assert result.inserted_count == 2


@pytest.mark.anyio
async def test_manual_collect_rate_limited_within_60_seconds() -> None:
    repo = InMemoryBidRepository()
    source = FakeSource({"용역": [make_bid(1)]})
    await service.collect_latest(repo, source, trigger="manual", requested_by="u1")
    started = repo.runs[0].started_at

    with pytest.raises(CollectRateLimited) as exc_info:
        await service.collect_latest(repo, source, trigger="manual", now=started + timedelta(seconds=15))
    assert exc_info.value.retry_after == 45

    # 60초가 지나면 다시 허용, cron은 제한 없음
    await service.collect_latest(repo, source, trigger="manual", now=started + timedelta(seconds=61))
    await service.collect_latest(repo, source, trigger="cron")


@pytest.mark.anyio
async def test_collect_failure_is_recorded() -> None:
    repo = InMemoryBidRepository()

    with pytest.raises(CollectFailed):
        await service.collect_latest(repo, FakeSource(fail=True), trigger="cron")

    assert repo.runs[0].status == "failed"
    assert "ACCESS DENIED" in (repo.runs[0].error or "")


@pytest.mark.anyio
async def test_search_filters_and_order() -> None:
    repo = InMemoryBidRepository()
    await repo.upsert_bids(
        [
            make_bid(1, name="GIS DB 구축 용역", price=100_000_000, institution="광주광역시"),
            make_bid(2, name="도로 정비", price=None),
            make_bid(3, "공사", name="교량 보수 공사", price=300_000_000),
            make_bid(4, name="gis 유지보수", price=30_000_000, closing=datetime(2026, 10, 20, 10, 0, tzinfo=KST)),
        ]
    )

    all_items = await service.search_bids(repo, BidFilter())
    assert [b.bid_ntce_nm for b in all_items.items] == ["gis 유지보수", "교량 보수 공사", "도로 정비", "GIS DB 구축 용역"]

    assert (await service.search_bids(repo, BidFilter(q="GIS"))).total == 2  # 대소문자 무시 부분 일치
    assert (await service.search_bids(repo, BidFilter(category="공사"))).total == 1
    assert (await service.search_bids(repo, BidFilter(institution="광주"))).total == 1
    assert (await service.search_bids(repo, BidFilter(min_price=50_000_000))).total == 2  # 가격 없는 공고 제외
    closing = await service.search_bids(repo, BidFilter(closing_from=date(2026, 10, 20), closing_to=date(2026, 10, 20)))
    assert [b.bid_ntce_nm for b in closing.items] == ["gis 유지보수"]


@pytest.mark.anyio
async def test_search_pagination() -> None:
    repo = InMemoryBidRepository()
    await repo.upsert_bids([make_bid(i) for i in range(25)])

    page2 = await service.search_bids(repo, BidFilter(), page=2, size=10)

    assert page2.total == 25
    assert len(page2.items) == 10
    assert page2.items[0].bid_ntce_nm == "공고 14"


@pytest.mark.anyio
async def test_detail_includes_attachments() -> None:
    repo = InMemoryBidRepository()
    raw = {"ntceSpecDocUrl1": "https://a/1", "ntceSpecFileNm1": "공고서.hwp", "ntceSpecDocUrl2": "", "ntceSpecDocUrl3": "https://a/3"}
    await repo.upsert_bids([make_bid(1, raw=raw)])

    detail = await service.get_bid_detail(repo, 1)

    assert detail is not None
    assert [(a.name, a.url) for a in detail.attachments] == [("공고서.hwp", "https://a/1"), ("첨부파일 3", "https://a/3")]
    assert await service.get_bid_detail(repo, 999) is None


@pytest.mark.anyio
async def test_settings_update() -> None:
    repo = InMemoryBidRepository()
    assert (await service.get_settings(repo)).categories == ["용역"]

    updated = await service.update_settings(repo, ["물품", "외자"], 5, "u1")

    assert (updated.categories, updated.num_rows) == (["물품", "외자"], 5)
    assert (await repo.get_settings()).updated_by == "u1"
