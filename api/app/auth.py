"""인증 의존성.

- 사용자 API: web이 보낸 Supabase access_token을 Supabase Auth(`/auth/v1/user`)로 검증한다.
- Cron API: Vercel Cron이 보내는 `Authorization: Bearer <CRON_SECRET>`을 확인한다.
설정이 비어 있으면 통과시키지 않고 503을 반환한다 (안전한 기본값).
"""

import secrets
from dataclasses import dataclass

import httpx
from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


@dataclass
class CurrentUser:
    id: str
    email: str | None = None


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "로그인이 필요합니다.")
    return authorization[7:].strip()


async def get_current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    token = _bearer_token(authorization)
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "인증 설정이 아직 구성되지 않았습니다.")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "인증 서버에 연결하지 못했습니다.") from None
    if response.status_code != 200:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "로그인 정보가 유효하지 않습니다.")
    data = response.json()
    return CurrentUser(id=data["id"], email=data.get("email"))


def verify_cron_secret(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "CRON_SECRET이 설정되지 않았습니다.")
    expected = f"Bearer {settings.cron_secret}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Cron 인증 실패")
