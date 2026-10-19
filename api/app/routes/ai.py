"""D3 API: Agent 채팅, 적합도 추천, 👍/👎 (doc/data-contract.md 3.4). 모두 로그인 필요."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import CurrentUser, get_current_user
from app.deps import get_agent_llm, get_fast_llm, get_repository
from app.llm import LLMError, LLMProvider
from app.repository import BidRepository
from app.schemas import (
    ChatIn,
    ChatOut,
    RecommendationFeedbackIn,
    RecommendationFeedbackOut,
    RecommendationsOut,
)
from app.services import agent, recommend
from app.services.recommend import ProfileRequired

router = APIRouter(prefix="/api")


def _require(llm: LLMProvider | None) -> LLMProvider:
    if llm is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI 기능이 아직 설정되지 않았습니다.")
    return llm


@router.post("/agent/chat", response_model=ChatOut)
async def agent_chat(
    body: ChatIn,
    user: CurrentUser = Depends(get_current_user),
    repo: BidRepository = Depends(get_repository),
    llm: LLMProvider | None = Depends(get_agent_llm),
) -> ChatOut:
    try:
        return await agent.chat(repo, _require(llm), body.message, body.history, user_id=user.id)
    except LLMError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"AI 응답 실패: {exc}") from None


@router.get("/recommendations", response_model=RecommendationsOut)
async def get_recommendations(
    limit: int = Query(default=10, ge=1, le=20),
    user: CurrentUser = Depends(get_current_user),
    repo: BidRepository = Depends(get_repository),
    llm: LLMProvider | None = Depends(get_fast_llm),
) -> RecommendationsOut:
    try:
        return await recommend.get_recommendations(repo, _require(llm), user.id, limit=limit)
    except ProfileRequired as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from None


@router.post("/recommendations/{bid_id}/feedback", response_model=RecommendationFeedbackOut)
async def post_recommendation_feedback(
    bid_id: int,
    body: RecommendationFeedbackIn,
    user: CurrentUser = Depends(get_current_user),
    repo: BidRepository = Depends(get_repository),
) -> RecommendationFeedbackOut:
    result = await recommend.set_feedback(repo, user.id, bid_id, body.feedback)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "내 추천 목록에 없는 공고입니다.")
    return result
