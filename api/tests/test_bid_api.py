"""API 계약(doc/data-contract.md 3장) 검증. 인증·수집 소스·저장소는 가짜로 바꿔 끼운다."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user
from app.config import Settings, get_settings
from app.deps import get_bid_source, get_fast_llm, get_repository
from app.main import app
from app.repository import InMemoryBidRepository
from tests.fakes import FakeLLM, FakeSource, make_bid

CRON_SECRET = "test-cron-secret"


@pytest.fixture
def repo() -> InMemoryBidRepository:
    return InMemoryBidRepository()


@pytest.fixture
def source() -> FakeSource:
    return FakeSource({"용역": [make_bid(i) for i in range(3)], "공사": [make_bid(10, "공사", price=None)]})


@pytest.fixture
def llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def client(repo: InMemoryBidRepository, source: FakeSource, llm: FakeLLM) -> Iterator[TestClient]:
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_bid_source] = lambda: source
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="user-1")
    app.dependency_overrides[get_fast_llm] = lambda: llm
    app.dependency_overrides[get_settings] = lambda: Settings(cron_secret=CRON_SECRET, _env_file=None)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_collect_then_list_and_detail(client: TestClient) -> None:
    app.dependency_overrides[get_fast_llm] = lambda: None  # 요약 없는 상태의 계약 형식 확인
    response = client.post("/api/collect", json={"categories": ["용역", "공사"], "num_rows": 10})
    assert response.status_code == 200
    assert response.json() == {
        "run_id": 1,
        "status": "success",
        "categories": ["용역", "공사"],
        "fetched_count": 4,
        "inserted_count": 4,
    }

    listing = client.get("/api/bids", params={"size": 2}).json()
    assert listing["total"] == 4 and listing["page"] == 1 and listing["size"] == 2
    first = listing["items"][0]
    assert first["bid_ntce_no"] == "R26BK00000010"
    assert first["presmpt_prce"] is None
    assert first["summary"] is None
    assert first["bid_ntce_dt"].endswith("+09:00")  # 계약서 1장: ISO 8601 + KST
    assert "raw" not in first

    detail = client.get(f"/api/bids/{first['id']}").json()
    assert detail["attachments"] == []
    assert client.get("/api/bids/999").status_code == 404


def test_list_query_validation(client: TestClient) -> None:
    assert client.get("/api/bids", params={"size": 101}).status_code == 422
    assert client.get("/api/bids", params={"category": "기타"}).status_code == 422
    assert client.get("/api/bids", params={"category": "용역", "q": "공고"}).status_code == 200


def test_manual_collect_rate_limit_returns_429(client: TestClient) -> None:
    assert client.post("/api/collect").status_code == 200

    response = client.post("/api/collect")

    assert response.status_code == 429
    assert 0 < int(response.headers["Retry-After"]) <= 60


def test_collect_failure_returns_502(client: TestClient) -> None:
    app.dependency_overrides[get_bid_source] = lambda: FakeSource(fail=True)
    response = client.post("/api/collect")
    assert response.status_code == 502


def test_settings_get_and_put(client: TestClient) -> None:
    assert client.get("/api/settings").json()["categories"] == ["용역"]

    response = client.put("/api/settings", json={"categories": ["물품", "물품", "외자"], "num_rows": 5})

    assert response.status_code == 200
    body = response.json()
    assert (body["categories"], body["num_rows"]) == (["물품", "외자"], 5)
    assert body["updated_at"].endswith("+09:00")
    assert client.put("/api/settings", json={"categories": [], "num_rows": 5}).status_code == 422
    assert client.put("/api/settings", json={"categories": ["용역"], "num_rows": 101}).status_code == 422


def test_cron_requires_secret(client: TestClient) -> None:
    assert client.get("/api/cron/collect").status_code == 401
    assert client.get("/api/cron/collect", headers={"Authorization": "Bearer wrong"}).status_code == 401

    response = client.get("/api/cron/collect", headers={"Authorization": f"Bearer {CRON_SECRET}"})

    assert response.status_code == 200
    assert response.json()["categories"] == ["용역"]


def test_cron_disabled_without_secret(client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(cron_secret="", _env_file=None)
    assert client.get("/api/cron/collect", headers={"Authorization": "Bearer "}).status_code == 503


def test_profile_requires_consent_on_first_save(client: TestClient) -> None:
    assert client.get("/api/me/profile").status_code == 404

    body = {"company_name": "예시소프트", "industries": ["소프트웨어 개발"], "regions": ["서울"], "keywords": ["GIS"]}
    assert client.put("/api/me/profile", json=body).status_code == 400  # 동의 없음

    saved = client.put("/api/me/profile", json={**body, "consent": True})
    assert saved.status_code == 200
    consent_at = saved.json()["consent_at"]
    assert consent_at.endswith("+09:00")

    # 이후 수정은 동의 재확인 없이 가능하고, 최초 동의 시각은 유지된다
    updated = client.put("/api/me/profile", json={**body, "regions": ["경기"]}).json()
    assert updated["regions"] == ["경기"] and updated["consent_at"] == consent_at
    assert client.get("/api/me/profile").json()["regions"] == ["경기"]


def test_profile_price_range_validation(client: TestClient) -> None:
    body = {"min_price": 200, "max_price": 100, "consent": True}
    assert client.put("/api/me/profile", json=body).status_code == 400


def test_feedback_without_login(client: TestClient, repo: InMemoryBidRepository) -> None:
    app.dependency_overrides.pop(get_current_user)  # 실제 의존성: 토큰이 없으면 비로그인으로 처리
    response = client.post("/api/feedback", json={"rating": 4, "message": " 목록이 보기 편해요 ", "page": "/bids"})

    assert response.status_code == 201
    assert response.json() == {"id": 1}
    assert repo.feedbacks[0] == {"user_id": None, "rating": 4, "message": "목록이 보기 편해요", "page": "/bids"}
    assert client.post("/api/feedback", json={"rating": 6, "message": "x"}).status_code == 422
    assert client.post("/api/feedback", json={"rating": 3, "message": ""}).status_code == 422


def test_auth_required_endpoints_reject_missing_token(repo: InMemoryBidRepository, source: FakeSource) -> None:
    """실제 인증 의존성 사용: 토큰이 없으면 401, Supabase 설정이 없으면 503."""
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_bid_source] = lambda: source
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    app.dependency_overrides[get_fast_llm] = lambda: None
    try:
        client = TestClient(app)
        assert client.post("/api/collect").status_code == 401
        assert client.put("/api/settings", json={"categories": ["용역"], "num_rows": 10}).status_code == 401
        headers = {"Authorization": "Bearer some-token"}
        assert client.post("/api/collect", headers=headers).status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_collect_summarizes_new_bids(client: TestClient, llm: FakeLLM) -> None:
    client.post("/api/collect", json={"categories": ["용역"]})

    items = client.get("/api/bids").json()["items"]

    assert len(llm.prompts) == 3
    summary = items[0]["summary"]
    assert summary["summary"] == "첫째 줄\n둘째 줄\n셋째 줄"
    assert summary["ai_generated"] is True and summary["model"] == "fake-model"


def test_collect_succeeds_even_if_summary_fails(client: TestClient) -> None:
    app.dependency_overrides[get_fast_llm] = lambda: FakeLLM(fail_for={"공고"})

    response = client.post("/api/collect")

    assert response.status_code == 200
    assert response.json()["inserted_count"] == 3
    assert all(item["summary"] is None for item in client.get("/api/bids").json()["items"])
