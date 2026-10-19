"""Bid Agent 서비스·Claude 도구 루프 테스트 (실제 Claude를 호출하지 않는다)."""

import json
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from app.koneps.models import KST
from app.llm.base import LLMError, ToolSpec
from app.llm.claude import FALLBACK_BETA, ClaudeProvider
from app.repository import InMemoryBidRepository, ProfileRecord
from app.services import agent
from tests.fakes import FakeAgentLLM, make_bid

NOW = datetime(2026, 10, 19, 10, 0, tzinfo=KST)


def test_system_prompt_has_date_rules_and_profile() -> None:
    profile = ProfileRecord("u1", None, ["소프트웨어 개발"], ["서울"], None, 100_000_000, ["GIS"], NOW)

    prompt = agent.build_system_prompt(date(2026, 10, 19), profile)

    assert "오늘 날짜: 2026-10-19 (월요일, KST)" in prompt
    assert "도구 결과에 없는 공고·금액·조건은 만들지 않는다" in prompt
    assert "업종: 소프트웨어 개발" in prompt and "관심 금액: 제한 없음 ~ 100,000,000원" in prompt
    assert "회사 프로필" not in agent.build_system_prompt(date(2026, 10, 19), None)


@pytest.mark.anyio
async def test_chat_returns_cited_bids_in_mention_order() -> None:
    repo = InMemoryBidRepository()
    await repo.upsert_bids([make_bid(1, name="GIS 구축"), make_bid(2, name="GIS 유지보수"), make_bid(3, name="도로")])
    await repo.save_profile(ProfileRecord("u1", None, ["SW"], [], None, None, [], NOW))

    def answer(outputs: list[str]) -> str:
        items = json.loads(outputs[0])["items"]
        nums = {i["공고명"]: i["공고번호"] for i in items}
        return f"1. GIS 유지보수 ({nums['GIS 유지보수']})\n2. GIS 구축 ({nums['GIS 구축']})"

    llm = FakeAgentLLM([("search_bids", {"q": "GIS", "size": 5})], answer)
    out = await agent.chat(repo, llm, "GIS 공고 찾아줘", [], user_id="u1", now=NOW)

    assert [b.bid_ntce_nm for b in out.bids] == ["GIS 유지보수", "GIS 구축"]  # 언급 순서, 언급 안 한 공고 제외
    assert out.tool_calls[0].name == "search_bids" and out.tool_calls[0].args == {"q": "GIS", "size": 5}
    assert out.tool_calls[0].result_count == 2
    assert out.ai_generated and out.model == "fake-agent"
    assert "업종: SW" in llm.system  # 로그인 사용자의 프로필 반영
    assert llm.messages[-1] == {"role": "user", "content": "GIS 공고 찾아줘"}


@pytest.mark.anyio
async def test_chat_detail_tool_and_tool_errors() -> None:
    repo = InMemoryBidRepository()
    raw = {"ntceSpecFileNm1": "공고서.hwpx", "ntceSpecDocUrl1": "https://a/1"}
    await repo.upsert_bids([make_bid(1, name="안림지구 변경용역", raw=raw)])
    captured: list[str] = []

    def answer(outputs: list[str]) -> str:
        captured.extend(outputs)
        return "안림지구 변경용역 (R26BK00000001-000)"

    calls = [("get_bid_detail", {"id": 1}), ("get_bid_detail", {"id": 999}), ("search_bids", {"closing_from": "어제"})]
    out = await agent.chat(repo, FakeAgentLLM(calls, answer), "자세히", [], user_id=None, now=NOW)

    detail = json.loads(captured[0])
    assert detail["attachments"] == ["공고서.hwpx"] and detail["공고번호"] == "R26BK00000001-000"
    assert captured[1].startswith("오류:") and "없습니다" in captured[1]
    assert captured[2].startswith("오류: 검색 조건 형식 오류")
    assert [b.id for b in out.bids] == [1]


# ---------------------------------------------------------------- ClaudeProvider.run_agent (가짜 SDK)
def _block(**kw):
    return SimpleNamespace(**kw)


class _FakeBetaMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests: list[dict] = []

    async def create(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


def _provider(messages: _FakeBetaMessages, fallbacks: bool = True) -> ClaudeProvider:
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return ClaudeProvider("", "claude-sonnet-5-5", fallbacks=fallbacks, client=client)


TOOL = ToolSpec("search_bids", "검색", {"type": "object", "properties": {}})


@pytest.mark.anyio
async def test_run_agent_executes_tools_then_answers() -> None:
    first = SimpleNamespace(
        stop_reason="tool_use",
        model="claude-sonnet-5-5",
        content=[
            _block(type="thinking", thinking=""),
            _block(type="tool_use", id="t1", name="search_bids", input={"q": "GIS"}),
            _block(type="tool_use", id="t2", name="search_bids", input={"q": "오류"}),
        ],
    )
    final = SimpleNamespace(
        stop_reason="end_turn", model="claude-sonnet-5-5", content=[_block(type="text", text=" 답변 ")]
    )
    messages = _FakeBetaMessages([first, final])

    async def execute(name, args):
        if args["q"] == "오류":
            raise ValueError("잘못된 조건")
        return "결과", 3

    result = await _provider(messages).run_agent(
        system="s", messages=[{"role": "user", "content": "찾아줘"}], tools=[TOOL], execute=execute
    )

    assert result.text == "답변" and result.model == "claude-sonnet-5-5"
    assert [(c.name, c.args, c.result_count) for c in result.tool_calls] == [
        ("search_bids", {"q": "GIS"}, 3),
        ("search_bids", {"q": "오류"}, None),
    ]
    second = messages.requests[1]
    assert second["messages"][1]["role"] == "assistant"  # 생각·도구 호출 블록을 그대로 이어 붙임
    results = second["messages"][2]["content"]  # 두 결과를 한 user 메시지로
    assert results[0] == {"type": "tool_result", "tool_use_id": "t1", "content": "결과"}
    assert results[1]["is_error"] is True and "잘못된 조건" in results[1]["content"]
    first_req = messages.requests[0]
    assert first_req["tool_choice"] == {"type": "auto"} and first_req["output_config"] == {"effort": "low"}
    assert first_req["betas"] == [FALLBACK_BETA] and first_req["fallbacks"] == "default"


@pytest.mark.anyio
async def test_run_agent_last_step_disables_tools() -> None:
    loop = SimpleNamespace(
        stop_reason="tool_use", model="m", content=[_block(type="tool_use", id="t", name="search_bids", input={})]
    )
    final = SimpleNamespace(stop_reason="end_turn", model="m", content=[_block(type="text", text="끝")])
    messages = _FakeBetaMessages([loop, loop, final])

    async def execute(name, args):
        return "r", 0

    result = await _provider(messages, fallbacks=False).run_agent(
        system="s", messages=[{"role": "user", "content": "q"}], tools=[TOOL], execute=execute, max_steps=2
    )

    assert result.text == "끝"
    assert [r["tool_choice"]["type"] for r in messages.requests] == ["auto", "auto", "none"]
    assert "betas" not in messages.requests[0]


@pytest.mark.anyio
async def test_run_agent_refusal_raises() -> None:
    refusal = SimpleNamespace(stop_reason="refusal", model="m", content=[])
    with pytest.raises(LLMError):
        await _provider(_FakeBetaMessages([refusal])).run_agent(
            system="s", messages=[{"role": "user", "content": "q"}], tools=[TOOL], execute=None
        )
