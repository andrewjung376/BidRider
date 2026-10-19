"""회사 프로필(Long-term Memory)과 사용자 피드백."""

from datetime import datetime

from app.koneps.models import KST
from app.repository.base import BidRepository, ProfileRecord
from app.schemas import FeedbackOut, ProfileIn, ProfileOut


class ConsentRequired(Exception):
    """처음 저장할 때 개인정보 수집·이용 동의가 없다 (NFR-05)."""


async def get_profile(repo: BidRepository, user_id: str) -> ProfileOut | None:
    record = await repo.get_profile(user_id)
    return _to_out(record) if record else None


async def save_profile(
    repo: BidRepository, user_id: str, body: ProfileIn, now: datetime | None = None
) -> ProfileOut:
    existing = await repo.get_profile(user_id)
    if existing is None and not body.consent:
        raise ConsentRequired("처음 저장할 때 개인정보 수집·이용 동의가 필요합니다.")
    consent_at = existing.consent_at if existing else (now or datetime.now(KST))
    record = await repo.save_profile(
        ProfileRecord(user_id=user_id, consent_at=consent_at, **body.model_dump(exclude={"consent"}))
    )
    return _to_out(record)


async def add_feedback(
    repo: BidRepository, user_id: str | None, rating: int, message: str, page: str | None
) -> FeedbackOut:
    return FeedbackOut(id=await repo.add_feedback(user_id, rating, message.strip(), page))


async def delete_account(repo: BidRepository, user_id: str) -> None:
    """탈퇴 (NFR-05): 계정과 개인 데이터를 삭제한다."""
    await repo.delete_user(user_id)


def _to_out(record: ProfileRecord) -> ProfileOut:
    return ProfileOut(
        company_name=record.company_name,
        industries=record.industries,
        regions=record.regions,
        min_price=record.min_price,
        max_price=record.max_price,
        keywords=record.keywords,
        consent_at=record.consent_at,
    )
