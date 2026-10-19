"""프로필·피드백 API (doc/data-contract.md 3.3)."""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth import CurrentUser, get_current_user, get_optional_user
from app.deps import get_repository
from app.repository import BidRepository
from app.schemas import FeedbackIn, FeedbackOut, ProfileIn, ProfileOut
from app.services import profile as service
from app.services.profile import ConsentRequired

router = APIRouter(prefix="/api")


@router.get("/me/profile", response_model=ProfileOut)
async def get_profile(
    user: CurrentUser = Depends(get_current_user),
    repo: BidRepository = Depends(get_repository),
) -> ProfileOut:
    profile = await service.get_profile(repo, user.id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "프로필이 없습니다.")
    return profile


@router.put("/me/profile", response_model=ProfileOut)
async def put_profile(
    body: ProfileIn,
    user: CurrentUser = Depends(get_current_user),
    repo: BidRepository = Depends(get_repository),
) -> ProfileOut:
    if body.min_price is not None and body.max_price is not None and body.min_price > body.max_price:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "금액 하한이 상한보다 클 수 없습니다.")
    try:
        return await service.save_profile(repo, user.id, body)
    except ConsentRequired as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from None


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    user: CurrentUser = Depends(get_current_user),
    repo: BidRepository = Depends(get_repository),
) -> Response:
    await service.delete_account(repo, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
async def post_feedback(
    body: FeedbackIn,
    user: CurrentUser | None = Depends(get_optional_user),
    repo: BidRepository = Depends(get_repository),
) -> FeedbackOut:
    return await service.add_feedback(repo, user.id if user else None, body.rating, body.message, body.page)
