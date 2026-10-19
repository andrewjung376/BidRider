"""적합도 추천·👍/👎 서비스 테스트 (가짜 평가 LLM)."""

from datetime import datetime, timedelta

import pytest

from app.koneps.models import KST
from app.repository import InMemoryBidRepository, ProfileRecord
from app.services import recommend
from app.services.recommend import ProfileRequired
from tests.fakes import FakeScorer, make_bid

NOW = datetime(2026, 10, 19, 10, 0, tzinfo=KST)
FUTURE = datetime(2026, 11, 30, 10, 0, tzinfo=KST)


async def _setup(repo: InMemoryBidRepository) -> None:
    await repo.upsert_bids(
        [
            make_bid(1, name="GIS DB 구축", closing=FUTURE),
            make_bid(2, name="도로 정비", closing=FUTURE),
            make_bid(3, name="GIS 유지보수", closing=FUTURE),
            make_bid(4, name="마감 지난 GIS", closing=NOW - timedelta(days=1)),
        ]
    )
    await repo.save_profile(ProfileRecord("u1", "예시", ["소프트웨어 개발"], ["서울"], None, None, ["GIS"], NOW))


@pytest.mark.anyio
async def test_requires_profile() -> None:
    with pytest.raises(ProfileRequired):
        await recommend.get_recommendations(InMemoryBidRepository(), FakeScorer(), "u1", now=NOW)


@pytest.mark.anyio
async def test_scores_open_bids_sorted_and_cached() -> None:
    repo = InMemoryBidRepository()
    await _setup(repo)
    llm = FakeScorer({"GIS DB": 90, "GIS 유지": 80, "도로": 20})

    out = await recommend.get_recommendations(repo, llm, "u1", now=NOW)

    assert [(i.bid.bid_ntce_nm, i.score) for i in out.items] == [
        ("GIS DB 구축", 90),
        ("GIS 유지보수", 80),
        ("도로 정비", 20),
    ]
    assert out.pending == 0 and out.items[0].ai_generated and out.items[0].model == "fake-scorer"
    assert all("마감 지난" not in p for p in llm.prompts)  # 마감된 공고는 후보에서 제외
    assert "관심 키워드: GIS" in llm.prompts[0]

    again = await recommend.get_recommendations(repo, llm, "u1", now=NOW)
    assert len(llm.prompts) == 3 and [i.score for i in again.items] == [90, 80, 20]  # 저장된 결과 재사용


@pytest.mark.anyio
async def test_feedback_kept_on_reeval_and_used_as_memory() -> None:
    repo = InMemoryBidRepository()
    await _setup(repo)
    llm = FakeScorer({"GIS": 70})
    await recommend.get_recommendations(repo, llm, "u1", now=NOW)

    assert (await recommend.set_feedback(repo, "u1", 1, 1)).feedback == 1
    assert await recommend.set_feedback(repo, "u1", 999, 1) is None  # 추천 목록에 없는 공고
    await recommend.set_feedback(repo, "u1", 2, -1)

    # 프로필을 바꾸면 다시 평가하고, 👍/👎는 유지되며 다음 평가 프롬프트에 들어간다
    profile = await repo.get_profile("u1")
    profile.keywords = ["GIS", "DB"]
    await repo.save_profile(profile)
    llm.prompts.clear()
    out = await recommend.get_recommendations(repo, llm, "u1", now=NOW)

    assert len(llm.prompts) == 3
    assert "[이전에 👍한 공고]\n- GIS DB 구축" in llm.prompts[0]
    assert "[이전에 👎한 공고]\n- 도로 정비" in llm.prompts[0]
    assert {i.bid.id: i.feedback for i in out.items} == {1: 1, 2: -1, 3: None}


@pytest.mark.anyio
async def test_pending_when_eval_limit_reached(monkeypatch) -> None:
    monkeypatch.setattr(recommend, "EVAL_PER_REQUEST", 2)
    repo = InMemoryBidRepository()
    await _setup(repo)

    first = await recommend.get_recommendations(repo, FakeScorer(), "u1", now=NOW)
    second = await recommend.get_recommendations(repo, FakeScorer(), "u1", now=NOW)

    assert (len(first.items), first.pending) == (2, 1)
    assert (len(second.items), second.pending) == (3, 0)  # "더 불러오기"로 나머지 평가
