"""라우터 의존성. 테스트에서는 app.dependency_overrides로 바꿔 끼운다."""

import logging
from functools import lru_cache

from fastapi import Depends, HTTPException, status

from app.config import Settings, get_settings
from app.koneps.client import KonepsClient, KonepsError
from app.llm import LLMError, LLMProvider, create_provider
from app.repository import BidRepository, InMemoryBidRepository, SupabaseBidRepository
from app.services.bids import BidSource

logger = logging.getLogger("bidradar")


@lru_cache
def _memory_repository() -> InMemoryBidRepository:
    return InMemoryBidRepository()


@lru_cache
def _supabase_repository(url: str, service_key: str) -> SupabaseBidRepository:
    return SupabaseBidRepository(url, service_key)


def get_repository(settings: Settings = Depends(get_settings)) -> BidRepository:
    """Supabase 설정이 있으면 Supabase 저장소, 없으면 메모리 저장소(로컬 개발용)."""
    if settings.supabase_url and settings.supabase_service_role_key:
        return _supabase_repository(settings.supabase_url, settings.supabase_service_role_key)
    return _memory_repository()


@lru_cache
def _llm(provider: str, api_key: str, model: str, agent: bool) -> LLMProvider | None:
    try:
        return create_provider(provider, api_key=api_key, model=model, agent=agent)
    except LLMError as exc:
        logger.warning("LLM(%s)을 쓸 수 없어 해당 AI 기능을 건너뜁니다: %s", model, exc)
        return None


def get_fast_llm(settings: Settings = Depends(get_settings)) -> LLMProvider | None:
    """요약·추천 평가용 빠른 모델. 키가 없거나 제공자가 구현되지 않았으면 None."""
    return _llm(settings.llm_provider, settings.anthropic_api_key, settings.llm_model_fast, False)


def get_agent_llm(settings: Settings = Depends(get_settings)) -> LLMProvider | None:
    """Bid Agent(도구 호출)용 모델. 키가 없거나 제공자가 구현되지 않았으면 None."""
    return _llm(settings.llm_provider, settings.anthropic_api_key, settings.llm_model_agent, True)


def get_bid_source(settings: Settings = Depends(get_settings)) -> BidSource:
    try:
        return KonepsClient(settings.data_go_kr_service_key, settings.koneps_base_url)
    except KonepsError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from None
