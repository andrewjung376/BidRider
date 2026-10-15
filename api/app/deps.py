"""라우터 의존성. 테스트에서는 app.dependency_overrides로 바꿔 끼운다."""

from functools import lru_cache

from fastapi import Depends, HTTPException, status

from app.config import Settings, get_settings
from app.koneps.client import KonepsClient, KonepsError
from app.repository import BidRepository, InMemoryBidRepository, SupabaseBidRepository
from app.services.bids import BidSource


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


def get_bid_source(settings: Settings = Depends(get_settings)) -> BidSource:
    try:
        return KonepsClient(settings.data_go_kr_service_key, settings.koneps_base_url)
    except KonepsError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from None
