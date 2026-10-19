"""저장소 인터페이스. 메모리 구현(테스트·로컬)과 Supabase 구현(L6)이 같은 계약을 따른다."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from app.koneps.models import Bid
from app.schemas import BidFilter


@dataclass
class BidSummaryRecord:
    summary: str
    qualifications: str | None
    required_documents: list[str]
    provider: str
    model: str


@dataclass
class BidRecord:
    id: int
    bid: Bid
    summary: BidSummaryRecord | None = None


@dataclass
class SettingsRecord:
    categories: list[str]
    num_rows: int
    updated_at: datetime
    updated_by: str | None = None


@dataclass
class CollectRunRecord:
    id: int
    trigger: Literal["cron", "manual"]
    categories: list[str]
    status: Literal["running", "success", "failed"]
    started_at: datetime
    fetched_count: int = 0
    inserted_count: int = 0
    error: str | None = None
    requested_by: str | None = None
    finished_at: datetime | None = None


@dataclass
class ProfileRecord:
    user_id: str
    company_name: str | None
    industries: list[str]
    regions: list[str]
    min_price: int | None
    max_price: int | None
    keywords: list[str]
    consent_at: datetime
    updated_at: datetime | None = None  # 추천 재평가 판단용 (저장소가 채움)


@dataclass
class RecommendationRecord:
    bid_id: int
    score: int
    reason: str
    model: str
    feedback: int | None = None  # 1 = 👍, -1 = 👎
    updated_at: datetime | None = None


class RepositoryError(Exception):
    """저장소(Supabase) 호출 실패."""


class BidRepository(Protocol):
    async def upsert_bids(self, bids: list[Bid]) -> int:
        """(공고번호, 차수) 기준으로 저장하고, 새로 추가된 건수를 반환한다."""
        ...

    async def list_bids(self, filters: BidFilter, page: int, size: int) -> tuple[list[BidRecord], int]:
        """공고게시일시 내림차순 목록과 전체 건수."""
        ...

    async def get_bid(self, bid_id: int) -> BidRecord | None: ...

    async def get_settings(self) -> SettingsRecord: ...

    async def update_settings(self, categories: list[str], num_rows: int, updated_by: str | None) -> SettingsRecord: ...

    async def create_run(
        self, trigger: Literal["cron", "manual"], categories: list[str], requested_by: str | None
    ) -> CollectRunRecord: ...

    async def finish_run(
        self,
        run_id: int,
        status: Literal["success", "failed"],
        fetched_count: int,
        inserted_count: int,
        error: str | None = None,
    ) -> None: ...

    async def last_manual_run_started_at(self) -> datetime | None: ...

    async def list_unsummarized(self, limit: int) -> list[BidRecord]:
        """AI 요약이 없는 공고를 공고게시일시 내림차순으로 (raw 포함)."""
        ...

    async def save_summary(self, bid_id: int, summary: BidSummaryRecord) -> None:
        """bid_id 기준으로 저장(있으면 덮어쓰기)한다."""
        ...

    async def get_profile(self, user_id: str) -> ProfileRecord | None: ...

    async def save_profile(self, profile: ProfileRecord) -> ProfileRecord:
        """user_id 기준으로 저장(있으면 덮어쓰기)한다."""
        ...

    async def add_feedback(self, user_id: str | None, rating: int, message: str, page: str | None) -> int:
        """저장한 피드백 id를 반환한다."""
        ...

    async def list_recommendations(self, user_id: str) -> list[RecommendationRecord]: ...

    async def save_recommendation(self, user_id: str, record: RecommendationRecord) -> None:
        """(user_id, bid_id) 기준으로 점수·근거를 저장한다. 기존 👍/👎는 유지한다."""
        ...

    async def set_recommendation_feedback(self, user_id: str, bid_id: int, feedback: int | None) -> bool:
        """내 추천 목록에 없는 공고면 False."""
        ...

    async def delete_user(self, user_id: str) -> None:
        """사용자 계정을 삭제한다. 프로필·추천은 삭제, 피드백·수집 기록·설정의 사용자 연결은 해제 (NFR-05).
        이미 없는 계정이어도 오류로 보지 않는다."""
        ...
