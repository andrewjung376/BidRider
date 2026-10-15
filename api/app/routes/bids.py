"""공고·수집·설정 API (doc/data-contract.md 3.3)."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.auth import CurrentUser, get_current_user, verify_cron_secret
from app.deps import get_bid_source, get_fast_llm, get_repository
from app.llm import LLMProvider
from app.repository import BidRepository
from app.schemas import (
    BidDetailOut,
    BidFilter,
    BidListOut,
    Category,
    CollectIn,
    CollectOut,
    SettingsIn,
    SettingsOut,
)
from app.services import bids as service
from app.services import summaries
from app.services.bids import BidSource, CollectFailed, CollectRateLimited

logger = logging.getLogger("bidradar")
router = APIRouter(prefix="/api")

MANUAL_SUMMARY_TIMEOUT = 25.0  # "지금 수집": 화면에서 기다리는 요청
CRON_SUMMARY_TIMEOUT = 120.0  # Vercel 함수 제한 300초 안


@router.get("/bids", response_model=BidListOut)
async def list_bids(
    category: Category | None = None,
    q: str | None = None,
    institution: str | None = None,
    min_price: int | None = Query(default=None, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    closing_from: date | None = None,
    closing_to: date | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    repo: BidRepository = Depends(get_repository),
) -> BidListOut:
    filters = BidFilter(
        category=category,
        q=q or None,
        institution=institution or None,
        min_price=min_price,
        max_price=max_price,
        closing_from=closing_from,
        closing_to=closing_to,
    )
    return await service.search_bids(repo, filters, page, size)


@router.get("/bids/{bid_id}", response_model=BidDetailOut)
async def get_bid(bid_id: int, repo: BidRepository = Depends(get_repository)) -> BidDetailOut:
    detail = await service.get_bid_detail(repo, bid_id)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "공고를 찾을 수 없습니다.")
    return detail


@router.post("/collect", response_model=CollectOut)
async def collect(
    body: CollectIn | None = None,
    user: CurrentUser = Depends(get_current_user),
    repo: BidRepository = Depends(get_repository),
    source: BidSource = Depends(get_bid_source),
    llm: LLMProvider | None = Depends(get_fast_llm),
):
    body = body or CollectIn()
    try:
        result = await service.collect_latest(
            repo,
            source,
            trigger="manual",
            categories=body.categories,
            num_rows=body.num_rows,
            requested_by=user.id,
        )
    except CollectRateLimited as exc:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": str(exc)},
            headers={"Retry-After": str(exc.retry_after)},
        )
    except CollectFailed as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"수집 실패 (run {exc.run_id}): {exc}") from None
    # 사용자가 기다리는 요청이라 요약 시간을 짧게 둔다. 못 끝낸 공고는 다음 수집 때 요약한다.
    await _summarize_after_collect(repo, llm, timeout=MANUAL_SUMMARY_TIMEOUT)
    return result


@router.get("/cron/collect", response_model=CollectOut, dependencies=[Depends(verify_cron_secret)])
async def cron_collect(
    repo: BidRepository = Depends(get_repository),
    source: BidSource = Depends(get_bid_source),
    llm: LLMProvider | None = Depends(get_fast_llm),
) -> CollectOut:
    try:
        result = await service.collect_latest(repo, source, trigger="cron")
    except CollectFailed as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"수집 실패 (run {exc.run_id}): {exc}") from None
    await _summarize_after_collect(repo, llm, timeout=CRON_SUMMARY_TIMEOUT)
    return result


async def _summarize_after_collect(repo: BidRepository, llm: LLMProvider | None, *, timeout: float) -> None:
    """요약 실패는 수집 결과에 영향을 주지 않는다 (로그만 남긴다)."""
    if llm is None:
        return
    try:
        outcome = await summaries.summarize_missing(repo, llm, timeout=timeout)
        logger.info("요약 %d건, 실패 %d건, 시간 초과 %s", outcome.summarized, outcome.failed, outcome.timed_out)
    except Exception:
        logger.exception("수집 후 요약 처리 중 오류")


@router.get("/settings", response_model=SettingsOut)
async def get_settings(repo: BidRepository = Depends(get_repository)) -> SettingsOut:
    return await service.get_settings(repo)


@router.put("/settings", response_model=SettingsOut)
async def put_settings(
    body: SettingsIn,
    user: CurrentUser = Depends(get_current_user),
    repo: BidRepository = Depends(get_repository),
) -> SettingsOut:
    return await service.update_settings(repo, body.categories, body.num_rows, user.id)
