"""라우터 의존성. 테스트에서는 app.dependency_overrides로 바꿔 끼운다."""

from functools import lru_cache

from fastapi import Depends, HTTPException, status

from app.config import Settings, get_settings
from app.koneps.client import KonepsClient, KonepsError
from app.repository import BidRepository, InMemoryBidRepository
from app.services.bids import BidSource


@lru_cache
def _memory_repository() -> InMemoryBidRepository:
    return InMemoryBidRepository()


def get_repository() -> BidRepository:
    # TODO(L6): Supabase 키가 설정되면 SupabaseBidRepository를 반환
    return _memory_repository()


def get_bid_source(settings: Settings = Depends(get_settings)) -> BidSource:
    try:
        return KonepsClient(settings.data_go_kr_service_key, settings.koneps_base_url)
    except KonepsError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from None
