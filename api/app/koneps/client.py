"""나라장터 입찰공고 목록 조회 클라이언트.

- 업무 구분마다 오퍼레이션이 다르다 (CATEGORY_OPERATIONS).
- 응답은 공고게시일시 오름차순이다 (2026-10-15 실호출 확인). 최신 N건은 마지막 페이지에 있다.
- 오류 메시지에 인증키가 노출되지 않도록 마스킹한다.
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import unquote

import httpx

from app.koneps.models import Bid

KST = timezone(timedelta(hours=9))

CATEGORY_OPERATIONS: dict[str, str] = {
    "용역": "getBidPblancListInfoServc",
    "공사": "getBidPblancListInfoCnstwk",
    "물품": "getBidPblancListInfoThng",
    "외자": "getBidPblancListInfoFrgcpt",
}


class KonepsError(Exception):
    """공공데이터포털 호출 실패 (네트워크, 인증, 응답 형식 오류)."""


class KonepsClient:
    def __init__(
        self,
        service_key: str,
        base_url: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 20.0,
    ) -> None:
        if not service_key:
            raise KonepsError("DATA_GO_KR_SERVICE_KEY가 설정되지 않았습니다.")
        # Encoding 키(% 포함)를 넣어도 httpx가 다시 인코딩하지 않도록 원본 키로 되돌린다.
        self._key = unquote(service_key)
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._timeout = timeout

    async def fetch_latest(
        self,
        category: str = "용역",
        num_rows: int = 10,
        *,
        lookback_days: int = 3,
        now: datetime | None = None,
    ) -> list[Bid]:
        """조회 기간 안에서 공고게시일시가 가장 최근인 공고 num_rows건을 최신순으로 반환한다."""
        if category not in CATEGORY_OPERATIONS:
            raise ValueError(f"지원하지 않는 업무 구분: {category}")
        if not 1 <= num_rows <= 999:
            raise ValueError("num_rows는 1~999 사이여야 합니다.")

        end = now or datetime.now(KST)
        begin = end - timedelta(days=lookback_days)
        operation = CATEGORY_OPERATIONS[category]
        base_params = {
            "inqryDiv": 1,  # 공고게시일시 기준
            "inqryBgnDt": begin.strftime("%Y%m%d%H%M"),
            "inqryEndDt": end.strftime("%Y%m%d%H%M"),
        }

        async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout) as client:
            # 1) 전체 건수 확인 → 2) 마지막 페이지(부족하면 그 앞 페이지까지) 조회
            first = await self._call(client, operation, {**base_params, "numOfRows": num_rows, "pageNo": 1})
            total = int(first["totalCount"] or 0)
            if total == 0:
                return []
            last_page = math.ceil(total / num_rows)
            items: list[dict[str, Any]] = []
            pages = [last_page - 1, last_page] if total % num_rows and last_page > 1 else [last_page]
            for page in pages:
                body = first if page == 1 else await self._call(
                    client, operation, {**base_params, "numOfRows": num_rows, "pageNo": page}
                )
                items.extend(self._items(body))

        bids = [Bid.from_item(item, category) for item in items]
        bids.sort(key=lambda b: b.bid_ntce_dt or datetime.min, reverse=True)
        return bids[:num_rows]

    async def _call(self, client: httpx.AsyncClient, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/{operation}"
        try:
            response = await client.get(url, params={"serviceKey": self._key, "type": "json", **params})
        except httpx.HTTPError as exc:
            raise KonepsError(f"{operation} 호출 실패: {type(exc).__name__}") from None
        if response.status_code != 200:
            raise KonepsError(f"{operation} HTTP {response.status_code}: {self._mask(response.text[:300])}")
        try:
            data = response.json()
        except ValueError:
            # 인증키 오류 등은 type=json이어도 XML로 온다.
            raise KonepsError(f"{operation} 응답이 JSON이 아님: {self._mask(response.text[:300])}") from None

        header = data.get("response", {}).get("header", {})
        if header.get("resultCode") != "00":
            raise KonepsError(f"{operation} 오류 {header.get('resultCode')}: {header.get('resultMsg')}")
        return data["response"]["body"]

    @staticmethod
    def _items(body: dict[str, Any]) -> list[dict[str, Any]]:
        items = body.get("items") or []
        if isinstance(items, dict):  # 일부 응답은 {"item": [...]} 또는 {"item": {...}} 형태
            items = items.get("item") or []
        if isinstance(items, dict):
            items = [items]
        return items

    def _mask(self, text: str) -> str:
        return text.replace(self._key, "***") if self._key else text
