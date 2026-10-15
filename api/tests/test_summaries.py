"""AI 요약 서비스와 Claude 제공자 테스트 (실제 Claude를 호출하지 않는다)."""

from types import SimpleNamespace

import anthropic
import httpx
import pytest

from app.llm.base import LLMError
from app.llm.claude import ClaudeProvider
from app.repository import InMemoryBidRepository
from app.services import summaries
from app.services.summaries import SummaryDraft, build_prompt
from tests.fakes import FakeLLM, make_bid


def test_build_prompt_includes_known_fields_only() -> None:
    raw = {
        "bidNtceNm": "GIS DB 구축 용역",
        "presmptPrce": "164118182",
        "rgnLmtBidLocplcJdgmBssNm": "",
        "indstrytyLmtYn": "Y",
        "ntceInsttOfclTelNo": "062-000-0000",  # 담당자 연락처는 넣지 않는다
        "ntceSpecFileNm1": "공고서.hwpx",
        "ntceSpecFileNm2": "",
    }
    prompt = build_prompt(make_bid(1, name="GIS DB 구축 용역", raw=raw))

    assert "- 업무 구분: 용역" in prompt
    assert "- 공고명: GIS DB 구축 용역" in prompt
    assert "- 추정가격(원): 50000000" in prompt  # 정규화된 Bid 필드 우선
    assert "- 업종제한 여부: Y" in prompt
    assert "지역제한 판단기준" not in prompt  # 빈 값 제외
    assert "062-000-0000" not in prompt
    assert "- 첨부파일명: 공고서.hwpx" in prompt


@pytest.mark.anyio
async def test_summarize_missing_saves_and_normalizes() -> None:
    repo = InMemoryBidRepository()
    await repo.upsert_bids([make_bid(i) for i in range(3)])
    llm = FakeLLM()

    result = await summaries.summarize_missing(repo, llm)

    assert (result.summarized, result.failed, result.timed_out) == (3, 0, False)
    record = await repo.get_bid(1)
    assert record is not None and record.summary is not None
    assert record.summary.summary == "첫째 줄\n둘째 줄\n셋째 줄"  # 빈 줄·앞뒤 공백 정리
    assert record.summary.qualifications == "지역제한 없음"
    assert record.summary.required_documents == ["입찰참가신청서"]
    assert (record.summary.provider, record.summary.model) == ("fake", "fake-model")
    # 이미 요약된 공고는 다시 요약하지 않는다
    assert (await summaries.summarize_missing(repo, llm)).summarized == 0


@pytest.mark.anyio
async def test_one_failure_does_not_stop_others() -> None:
    repo = InMemoryBidRepository()
    await repo.upsert_bids([make_bid(i) for i in range(3)])

    result = await summaries.summarize_missing(repo, FakeLLM(fail_for={"공고 1"}))

    assert (result.summarized, result.failed) == (2, 1)
    assert len(await repo.list_unsummarized(10)) == 1


@pytest.mark.anyio
async def test_timeout_keeps_finished_summaries() -> None:
    repo = InMemoryBidRepository()
    await repo.upsert_bids([make_bid(i) for i in range(4)])

    result = await summaries.summarize_missing(repo, FakeLLM(delay=0.05), concurrency=1, timeout=0.12)

    assert result.timed_out
    assert 1 <= result.summarized < 4


# ---------------------------------------------------------------- ClaudeProvider (가짜 SDK 클라이언트)
class _FakeMessages:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response, self.error, self.kwargs = response, error, None

    async def parse(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


def _provider(messages: _FakeMessages) -> ClaudeProvider:
    return ClaudeProvider("", "claude-haiku-5-5", client=SimpleNamespace(messages=messages))


@pytest.mark.anyio
async def test_claude_provider_returns_parsed_output() -> None:
    draft = SummaryDraft(summary="a\nb\nc", qualifications=None, required_documents=[])
    messages = _FakeMessages(SimpleNamespace(stop_reason="end_turn", parsed_output=draft))

    result = await _provider(messages).structured(system="s", prompt="p", output_type=SummaryDraft)

    assert result == draft
    assert messages.kwargs["model"] == "claude-haiku-5-5"
    assert messages.kwargs["output_format"] is SummaryDraft
    assert messages.kwargs["output_config"] == {"effort": "low"}


@pytest.mark.anyio
@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
async def test_claude_provider_rejects_incomplete_output(stop_reason: str) -> None:
    messages = _FakeMessages(SimpleNamespace(stop_reason=stop_reason, parsed_output=None))
    with pytest.raises(LLMError):
        await _provider(messages).structured(system="s", prompt="p", output_type=SummaryDraft)


@pytest.mark.anyio
async def test_claude_provider_maps_api_errors() -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    error = anthropic.RateLimitError("rate", response=httpx.Response(429, request=request), body=None)
    with pytest.raises(LLMError, match="한도"):
        await _provider(_FakeMessages(error=error)).structured(system="s", prompt="p", output_type=SummaryDraft)


def test_claude_provider_requires_key() -> None:
    with pytest.raises(LLMError):
        ClaudeProvider("", "claude-haiku-5-5")
