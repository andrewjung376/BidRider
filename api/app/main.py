"""BidRadar API 진입점."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.repository import RepositoryError
from app.routes.bids import router as bids_router
from app.routes.me import router as me_router

logger = logging.getLogger("bidradar")

app = FastAPI(title="BidRadar API", version="0.1.0")
app.include_router(bids_router)
app.include_router(me_router)


@app.exception_handler(RepositoryError)
async def repository_error_handler(request: Request, exc: RepositoryError) -> JSONResponse:
    # 상세 원인은 서버 로그에만 남기고, 클라이언트에는 일반 메시지만 준다.
    logger.error("저장소 오류 %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content={"detail": "저장소 처리 중 오류가 발생했습니다."})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
