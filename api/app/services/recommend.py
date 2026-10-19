"""적합도 추천 (FR-06)과 👍/👎 (FR-08) — Long-term Memory.

- 후보: 아직 마감되지 않은 최신 공고
- 평가: 빠른 모델의 구조화 출력(점수 0~100, 근거). 결과는 저장해 두고, 새 공고와 프로필을 바꾼 뒤의 공고만 다시 평가한다.
- 기억: 회사 프로필 + 이전 👍/👎 공고를 다음 평가 프롬프트에 넣는다.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field

from app.koneps.models import KST
from app.llm.base import LLMError, LLMProvider
from app.repository.base import BidRecord, BidRepository, ProfileRecord, RecommendationRecord
from app.schemas import BidFilter, RecommendationFeedbackOut, RecommendationOut, RecommendationsOut
from app.services.bids import to_bid_out
from app.services.summaries import build_prompt

logger = logging.getLogger("bidradar.recommend")

CANDIDATE_LIMIT = 30  # 평가 대상 후보 (마감 전 최신 공고)
EVAL_PER_REQUEST = 10  # 한 번 요청에서 새로 평가하는 최대 건수
EVAL_CONCURRENCY = 5
EVAL_TIMEOUT = 25.0  # 초. 응답 최대 약 30초 (계약서 3.4)
MEMORY_LIMIT = 5  # 프롬프트에 넣을 👍·👎 공고 수 (각각)

SYSTEM_PROMPT = """당신은 중소기업의 공공입찰 담당자를 돕는 분석가다. 회사 프로필과 입찰공고 정보를 보고, 이 회사가 참여를 검토할 만한지 적합도를 평가한다.

규칙:
- score: 0~100 정수. 업종·사업 내용 일치를 가장 중요하게 보고, 지역(지역제한·공동도급 의무지역), 추정가격과 관심 금액 범위, 관심 키워드를 함께 본다.
  80 이상 = 업종과 핵심 조건이 잘 맞음, 50~79 = 일부 맞음, 50 미만 = 업종이 다르거나 참여가 어려움.
- 사용자가 이전에 👍한 공고와 비슷하면 점수를 높이고, 👎한 공고와 비슷하면 낮춘다.
- reason: 판단 근거를 한국어 1~2문장("~다"체)으로 쓴다. 공고 정보와 프로필에 있는 사실만 근거로 쓰고 추측하지 않는다.
- 프로필 항목이 비어 있으면 그 기준은 감점하지 않는다."""


class ProfileRequired(Exception):
    """프로필이 없어 추천할 수 없다 (404)."""


class RecommendationDraft(BaseModel):
    score: int = Field(ge=0, le=100, description="적합도 0~100")
    reason: str = Field(description="판단 근거 1~2문장")


@dataclass
class _Memory:
    liked: list[str]
    disliked: list[str]


async def get_recommendations(
    repo: BidRepository,
    llm: LLMProvider,
    user_id: str,
    *,
    limit: int = 10,
    now: datetime | None = None,
    timeout: float = EVAL_TIMEOUT,
) -> RecommendationsOut:
    profile = await repo.get_profile(user_id)
    if profile is None:
        raise ProfileRequired("프로필이 없습니다.")

    today = (now or datetime.now(KST)).date()
    candidates, _ = await repo.list_bids(BidFilter(closing_from=today), 1, CANDIDATE_LIMIT)
    saved = {r.bid_id: r for r in await repo.list_recommendations(user_id)}

    to_eval = [c for c in candidates if _needs_eval(saved.get(c.id), profile)]
    batch = to_eval[:EVAL_PER_REQUEST]
    if batch:
        memory = await _memory(repo, saved)
        saved.update(await _evaluate(repo, llm, user_id, profile, memory, batch, saved, timeout))
    pending = len([c for c in to_eval if _needs_eval(saved.get(c.id), profile)])

    items = [
        RecommendationOut(
            bid=to_bid_out(c),
            score=saved[c.id].score,
            reason=saved[c.id].reason,
            feedback=saved[c.id].feedback,
            model=saved[c.id].model,
        )
        for c in candidates
        if c.id in saved and not _needs_eval(saved[c.id], profile)
    ]
    items.sort(key=lambda i: (i.score, i.bid.bid_ntce_dt or datetime.min.replace(tzinfo=KST)), reverse=True)
    return RecommendationsOut(items=items[:limit], pending=pending)


async def set_feedback(
    repo: BidRepository, user_id: str, bid_id: int, feedback: int | None
) -> RecommendationFeedbackOut | None:
    if not await repo.set_recommendation_feedback(user_id, bid_id, feedback):
        return None
    return RecommendationFeedbackOut(bid_id=bid_id, feedback=feedback)


def build_eval_prompt(profile: ProfileRecord, memory: _Memory, bid: BidRecord) -> str:
    lines = [
        "[회사 프로필]",
        f"- 회사명: {profile.company_name or '미입력'}",
        f"- 업종: {', '.join(profile.industries) or '미입력'}",
        f"- 지역: {', '.join(profile.regions) or '미입력'}",
        f"- 관심 금액: {_price(profile.min_price)} ~ {_price(profile.max_price)}",
        f"- 관심 키워드: {', '.join(profile.keywords) or '미입력'}",
    ]
    if memory.liked:
        lines += ["", "[이전에 👍한 공고]"] + [f"- {name}" for name in memory.liked]
    if memory.disliked:
        lines += ["", "[이전에 👎한 공고]"] + [f"- {name}" for name in memory.disliked]
    summary = bid.summary.summary if bid.summary else None
    lines += ["", "[평가할 입찰공고]", build_prompt(bid.bid).split("\n\n", 1)[1]]
    if summary:
        lines.append(f"- AI 요약: {summary.replace(chr(10), ' ')}")
    return "\n".join(lines)


def _needs_eval(record: RecommendationRecord | None, profile: ProfileRecord) -> bool:
    if record is None:
        return True
    # 프로필을 바꾼 뒤에 평가한 결과만 유효하다
    return bool(profile.updated_at and record.updated_at and record.updated_at < profile.updated_at)


async def _memory(repo: BidRepository, saved: dict[int, RecommendationRecord]) -> _Memory:
    async def names(value: int) -> list[str]:
        ids = [r.bid_id for r in saved.values() if r.feedback == value][:MEMORY_LIMIT]
        records = [await repo.get_bid(i) for i in ids]
        return [r.bid.bid_ntce_nm for r in records if r]

    return _Memory(liked=await names(1), disliked=await names(-1))


async def _evaluate(
    repo: BidRepository,
    llm: LLMProvider,
    user_id: str,
    profile: ProfileRecord,
    memory: _Memory,
    batch: list[BidRecord],
    previous: dict[int, RecommendationRecord],
    timeout: float,
) -> dict[int, RecommendationRecord]:
    done: dict[int, RecommendationRecord] = {}
    semaphore = asyncio.Semaphore(EVAL_CONCURRENCY)

    async def one(bid: BidRecord) -> None:
        async with semaphore:
            try:
                draft = await llm.structured(
                    system=SYSTEM_PROMPT,
                    prompt=build_eval_prompt(profile, memory, bid),
                    output_type=RecommendationDraft,
                )
            except LLMError as exc:
                logger.warning("추천 평가 실패 bid_id=%s: %s", bid.id, exc)
                return
            before = previous.get(bid.id)
            record = RecommendationRecord(
                bid_id=bid.id,
                score=draft.score,
                reason=draft.reason.strip(),
                model=llm.model,
                feedback=before.feedback if before else None,  # 다시 평가해도 👍/👎는 유지
            )
            await repo.save_recommendation(user_id, record)
            record.updated_at = datetime.now(KST)
            done[bid.id] = record

    try:
        await asyncio.wait_for(asyncio.gather(*(one(b) for b in batch)), timeout)
    except TimeoutError:
        logger.warning("추천 평가 제한 시간 %.0f초 초과: %d건 완료", timeout, len(done))
    return done


def _price(value: int | None) -> str:
    return f"{value:,}원" if value is not None else "제한 없음"
