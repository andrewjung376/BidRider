"""SupabaseBidRepository 요청 형식 검증 (가짜 PostgREST 응답 사용).

실제 Supabase 저장 확인은 RUN_LIVE=1 일 때만 test_live_supabase_roundtrip이 실행한다.
"""

import json
import os
from datetime import date, datetime

import httpx
import pytest

from app.koneps.models import KST
from app.repository import ProfileRecord, RepositoryError, SupabaseBidRepository
from app.schemas import BidFilter
from tests.fakes import make_bid

URL = "https://example.supabase.co"


def _repo(handler, key: str = "sb_secret_test") -> SupabaseBidRepository:
    return SupabaseBidRepository(URL, key, transport=httpx.MockTransport(handler))


def _bid_row(i: int, **extra) -> dict:
    return {
        "id": i,
        "bid_ntce_no": f"R26BK{i:08d}",
        "bid_ntce_ord": "000",
        "category": "용역",
        "bid_ntce_nm": f"공고 {i}",
        "ntce_instt_nm": "서울특별시",
        "dminstt_nm": None,
        "presmpt_prce": 1000,
        "bid_ntce_dt": "2026-10-15T09:30:40+00:00",
        "bid_clse_dt": None,
        "openg_dt": None,
        "bid_ntce_dtl_url": None,
        **extra,
    }


def test_headers_for_new_and_legacy_keys() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    import asyncio

    asyncio.run(_repo(handler, "sb_secret_x").get_bid(1))
    asyncio.run(_repo(handler, "eyJlegacy").get_bid(1))

    assert seen[0].headers["apikey"] == "sb_secret_x" and "authorization" not in seen[0].headers
    assert seen[1].headers["authorization"] == "Bearer eyJlegacy"


@pytest.mark.anyio
async def test_upsert_counts_only_new_rows() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[{"bid_ntce_no": "R26BK00000001", "bid_ntce_ord": "000"}])
        return httpx.Response(201)

    inserted = await _repo(handler).upsert_bids([make_bid(1), make_bid(2), make_bid(2)])

    assert inserted == 1
    get, post = calls
    assert get.url.params["bid_ntce_no"].startswith("in.(")
    assert post.url.params["on_conflict"] == "bid_ntce_no,bid_ntce_ord"
    assert post.headers["prefer"] == "resolution=merge-duplicates,return=minimal"
    body = json.loads(post.content)
    assert len(body) == 2  # 같은 요청 안의 중복 제거
    assert body[0]["bid_ntce_dt"].endswith("+09:00") and "raw" in body[0]


@pytest.mark.anyio
async def test_list_bids_params_total_and_kst() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        rows = [
            _bid_row(1, bid_summaries={"summary": "요약", "qualifications": None, "required_documents": ["서류"], "provider": "claude", "model": "m"}),
            _bid_row(2, bid_summaries=[]),
        ]
        return httpx.Response(200, json=rows, headers={"Content-Range": "20-21/57"})

    filters = BidFilter(
        category="용역", q="GIS*", institution="광주(청사)", min_price=10, max_price=20,
        closing_from=date(2026, 10, 16), closing_to=date(2026, 10, 20),
    )
    records, total = await _repo(handler).list_bids(filters, page=2, size=20)

    assert total == 57
    assert records[0].summary is not None and records[0].summary.required_documents == ["서류"]
    assert records[1].summary is None
    assert records[0].bid.bid_ntce_dt == datetime(2026, 10, 15, 18, 30, 40, tzinfo=KST)
    assert records[0].bid.bid_ntce_dt.utcoffset() == KST.utcoffset(None)

    params = captured[0].url.params
    assert captured[0].headers["prefer"] == "count=exact"
    assert params["offset"] == "20" and params["limit"] == "20"
    assert params["order"] == "bid_ntce_dt.desc.nullslast,id.desc"
    assert params["category"] == "eq.용역"
    assert params["bid_ntce_nm"] == "ilike.*GIS*"  # 사용자 입력의 * 제거
    assert params["or"] == '(ntce_instt_nm.ilike."*광주청사*",dminstt_nm.ilike."*광주청사*")'
    assert params.get_list("presmpt_prce") == ["gte.10", "lte.20"]
    assert params.get_list("bid_clse_dt") == ["gte.2026-10-16T00:00:00+09:00", "lte.2026-10-20T23:59:59.999999+09:00"]


@pytest.mark.anyio
async def test_empty_list_total_zero() -> None:
    repo = _repo(lambda r: httpx.Response(200, json=[], headers={"Content-Range": "*/0"}))
    assert await repo.list_bids(BidFilter(), 1, 20) == ([], 0)


@pytest.mark.anyio
async def test_settings_runs_profile_feedback() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        path = request.url.path
        if path.endswith("/collect_settings"):
            return httpx.Response(200, json=[{"id": 1, "categories": ["공사"], "num_rows": 5, "updated_by": "u1", "updated_at": "2026-10-16T00:00:00+00:00"}])
        if path.endswith("/collect_runs") and request.method == "POST":
            return httpx.Response(201, json=[{"id": 9, "trigger": "manual", "categories": ["공사"], "status": "running", "started_at": "2026-10-16T00:00:00+00:00", "requested_by": "u1"}])
        if path.endswith("/collect_runs") and request.method == "GET":
            return httpx.Response(200, json=[{"started_at": "2026-10-16T00:00:00+00:00"}])
        if path.endswith("/collect_runs"):
            return httpx.Response(204)
        if path.endswith("/profiles"):
            return httpx.Response(200, json=[{"user_id": "u1", "company_name": None, "industries": ["SW"], "regions": [], "min_price": None, "max_price": None, "keywords": [], "consent_at": "2026-10-16T00:00:00+00:00"}])
        if path.endswith("/feedbacks"):
            return httpx.Response(201, json=[{"id": 7}])
        return httpx.Response(404)

    repo = _repo(handler)
    settings = await repo.update_settings(["공사"], 5, "u1")
    run = await repo.create_run("manual", ["공사"], "u1")
    await repo.finish_run(run.id, "success", 3, 1)
    last = await repo.last_manual_run_started_at()
    profile = await repo.save_profile(
        ProfileRecord("u1", None, ["SW"], [], None, None, [], datetime(2026, 10, 16, 9, tzinfo=KST))
    )
    feedback_id = await repo.add_feedback(None, 5, "좋아요", "/bids")

    assert settings.updated_at.isoformat() == "2026-10-16T09:00:00+09:00"
    assert run.id == 9 and last == datetime(2026, 10, 16, 9, tzinfo=KST)
    assert profile.industries == ["SW"] and feedback_id == 7

    patch_settings = calls[0]
    assert patch_settings.method == "PATCH" and patch_settings.url.params["id"] == "eq.1"
    finish = next(c for c in calls if c.method == "PATCH" and c.url.path.endswith("/collect_runs"))
    assert finish.url.params["id"] == "eq.9" and json.loads(finish.content)["status"] == "success"
    upsert_profile = next(c for c in calls if c.url.path.endswith("/profiles"))
    assert upsert_profile.url.params["on_conflict"] == "user_id"


@pytest.mark.anyio
async def test_http_error_raises_repository_error() -> None:
    repo = _repo(lambda r: httpx.Response(400, json={"message": "bad"}))
    with pytest.raises(RepositoryError, match="400"):
        await repo.get_settings()


@pytest.mark.anyio
@pytest.mark.skipif(os.getenv("RUN_LIVE") != "1", reason="실제 Supabase 확인은 RUN_LIVE=1일 때만")
async def test_live_supabase_read() -> None:
    from app.config import get_settings

    s = get_settings()
    repo = SupabaseBidRepository(s.supabase_url, s.supabase_service_role_key)
    settings = await repo.get_settings()
    _, total = await repo.list_bids(BidFilter(), 1, 1)

    assert settings.categories
    assert total >= 0


@pytest.mark.anyio
async def test_unsummarized_and_save_summary_requests() -> None:
    from app.repository import BidSummaryRecord

    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[_bid_row(1, raw={"bidNtceNm": "x"}, bid_summaries=None)])
        return httpx.Response(201)

    repo = _repo(handler)
    records = await repo.list_unsummarized(5)
    await repo.save_summary(1, BidSummaryRecord("요약", None, [], "claude", "claude-haiku-5-5"))

    get, post = calls
    assert get.url.params["bid_summaries"] == "is.null" and get.url.params["limit"] == "5"
    assert records[0].bid.raw == {"bidNtceNm": "x"} and records[0].summary is None
    assert post.url.path.endswith("/bid_summaries") and post.url.params["on_conflict"] == "bid_id"
    assert json.loads(post.content)["required_documents"] == []


@pytest.mark.anyio
async def test_page_beyond_last_returns_empty_list() -> None:
    """PostgREST는 범위를 넘는 offset에 416(PGRST103)을 준다 → 오류가 아니라 빈 목록."""
    repo = _repo(
        lambda r: httpx.Response(
            416,
            json={"code": "PGRST103", "message": "Requested range not satisfiable"},
            headers={"Content-Range": "*/10"},
        )
    )

    assert await repo.list_bids(BidFilter(), page=5, size=20) == ([], 10)


@pytest.mark.anyio
async def test_416_on_other_requests_is_still_an_error() -> None:
    repo = _repo(lambda r: httpx.Response(416, json={"code": "PGRST103"}))
    with pytest.raises(RepositoryError, match="416"):
        await repo.get_bid(1)


@pytest.mark.anyio
@pytest.mark.parametrize("status", [200, 404])
async def test_delete_user_calls_auth_admin(status: int) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status, json={})

    await _repo(handler, key="sb_secret_x").delete_user("u-1")  # 404(이미 삭제)도 오류 아님

    assert calls[0].method == "DELETE"
    assert str(calls[0].url) == "https://example.supabase.co/auth/v1/admin/users/u-1"
    assert calls[0].headers["apikey"] == "sb_secret_x"


@pytest.mark.anyio
async def test_delete_user_error_raises() -> None:
    repo = _repo(lambda r: httpx.Response(403, json={"msg": "forbidden"}))
    with pytest.raises(RepositoryError, match="403"):
        await repo.delete_user("u-1")



@pytest.mark.anyio
async def test_recommendation_requests() -> None:
    from app.repository import RecommendationRecord

    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[{"bid_id": 3, "score": 80, "reason": "r", "feedback": 1, "model": "m", "updated_at": "2026-10-19T00:00:00+00:00"}])
        if request.method == "PATCH":
            return httpx.Response(200, json=[] if "999" in str(request.url) else [{"bid_id": 3}])
        return httpx.Response(201)

    repo = _repo(handler)
    recs = await repo.list_recommendations("u1")
    await repo.save_recommendation("u1", RecommendationRecord(bid_id=3, score=70, reason="새 근거", model="m"))
    ok = await repo.set_recommendation_feedback("u1", 3, -1)
    missing = await repo.set_recommendation_feedback("u1", 999, 1)

    assert recs[0].feedback == 1 and recs[0].updated_at.utcoffset() == KST.utcoffset(None)
    get, post, patch, _ = calls
    assert get.url.params["user_id"] == "eq.u1"
    assert post.url.params["on_conflict"] == "user_id,bid_id"
    assert "feedback" not in json.loads(post.content)  # 재평가해도 기존 👍/👎 유지
    assert patch.url.params["bid_id"] == "eq.3" and json.loads(patch.content) == {"feedback": -1}
    assert ok is True and missing is False
