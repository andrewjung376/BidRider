"""Supabase 저장소. PostgREST(`/rest/v1`)를 httpx로 직접 호출한다.

- service role 키로 접근하므로 RLS를 우회한다 (api 전용, doc/data-contract.md 2.9).
- 시각은 DB(UTC)에서 읽은 값을 KST로 바꿔 돌려준다 (계약서 1장).
"""

from datetime import datetime, time
from typing import Any, Literal

import httpx

from app.koneps.models import KST, Bid
from app.repository.base import (
    BidRecord,
    BidSummaryRecord,
    CollectRunRecord,
    ProfileRecord,
    RepositoryError,
    SettingsRecord,
)
from app.schemas import BidFilter

LIST_COLUMNS = (
    "id,bid_ntce_no,bid_ntce_ord,category,bid_ntce_nm,ntce_instt_nm,dminstt_nm,presmpt_prce,"
    "bid_ntce_dt,bid_clse_dt,openg_dt,bid_ntce_dtl_url"
)
SUMMARY_EMBED = "bid_summaries(summary,qualifications,required_documents,provider,model)"


class SupabaseBidRepository:
    def __init__(
        self,
        url: str,
        service_key: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._base = f"{url.rstrip('/')}/rest/v1"
        self._auth_admin = f"{url.rstrip('/')}/auth/v1/admin"
        self._headers = {"apikey": service_key}
        if not service_key.startswith("sb_"):  # 기존 방식(JWT) service_role 키
            self._headers["Authorization"] = f"Bearer {service_key}"
        self._transport = transport
        self._timeout = timeout

    # ---------------------------------------------------------------- 공고
    async def upsert_bids(self, bids: list[Bid]) -> int:
        unique = {(b.bid_ntce_no, b.bid_ntce_ord): b for b in bids}  # 같은 요청 안의 중복 제거
        if not unique:
            return 0
        numbers = ",".join(f'"{no}"' for no in {no for no, _ in unique})
        existing = await self._request(
            "GET", "/bids", params={"select": "bid_ntce_no,bid_ntce_ord", "bid_ntce_no": f"in.({numbers})"}
        )
        existing_keys = {(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in existing}

        rows = [_bid_row(b) for b in unique.values()]
        await self._request(
            "POST",
            "/bids",
            params={"on_conflict": "bid_ntce_no,bid_ntce_ord"},
            json=rows,
            prefer="resolution=merge-duplicates,return=minimal",
        )
        return len(unique.keys() - existing_keys)

    async def list_bids(self, filters: BidFilter, page: int, size: int) -> tuple[list[BidRecord], int]:
        params: list[tuple[str, str]] = [
            ("select", f"{LIST_COLUMNS},{SUMMARY_EMBED}"),
            ("order", "bid_ntce_dt.desc.nullslast,id.desc"),
            ("limit", str(size)),
            ("offset", str((page - 1) * size)),
        ]
        params += _filter_params(filters)
        response = await self._send("GET", "/bids", params=params, prefer="count=exact", allow_status={416})
        total = _total_from_content_range(response.headers.get("content-range"))
        if response.status_code == 416:  # 마지막 페이지를 넘는 offset (PGRST103): 빈 목록
            return [], total
        return [_bid_record(row) for row in response.json()], total

    async def get_bid(self, bid_id: int) -> BidRecord | None:
        rows = await self._request(
            "GET", "/bids", params={"select": f"*,{SUMMARY_EMBED}", "id": f"eq.{bid_id}"}
        )
        return _bid_record(rows[0]) if rows else None

    async def list_unsummarized(self, limit: int) -> list[BidRecord]:
        # 임베드 + is.null 필터 = 요약이 없는 공고만 (PostgREST anti-join)
        rows = await self._request(
            "GET",
            "/bids",
            params={
                "select": "*,bid_summaries(bid_id)",
                "bid_summaries": "is.null",
                "order": "bid_ntce_dt.desc.nullslast,id.desc",
                "limit": str(limit),
            },
        )
        return [_bid_record({**row, "bid_summaries": None}) for row in rows]

    async def save_summary(self, bid_id: int, summary: BidSummaryRecord) -> None:
        await self._request(
            "POST",
            "/bid_summaries",
            params={"on_conflict": "bid_id"},
            json={
                "bid_id": bid_id,
                "summary": summary.summary,
                "qualifications": summary.qualifications,
                "required_documents": summary.required_documents,
                "provider": summary.provider,
                "model": summary.model,
            },
            prefer="resolution=merge-duplicates,return=minimal",
        )

    # ---------------------------------------------------------------- 수집 설정·기록
    async def get_settings(self) -> SettingsRecord:
        rows = await self._request("GET", "/collect_settings", params={"select": "*", "id": "eq.1"})
        if not rows:
            raise RepositoryError("collect_settings 기본 행이 없습니다.")
        return _settings_record(rows[0])

    async def update_settings(self, categories: list[str], num_rows: int, updated_by: str | None) -> SettingsRecord:
        rows = await self._request(
            "PATCH",
            "/collect_settings",
            params={"id": "eq.1"},
            json={"categories": categories, "num_rows": num_rows, "updated_by": updated_by},
            prefer="return=representation",
        )
        return _settings_record(rows[0])

    async def create_run(
        self, trigger: Literal["cron", "manual"], categories: list[str], requested_by: str | None
    ) -> CollectRunRecord:
        rows = await self._request(
            "POST",
            "/collect_runs",
            json={"trigger": trigger, "categories": categories, "status": "running", "requested_by": requested_by},
            prefer="return=representation",
        )
        row = rows[0]
        return CollectRunRecord(
            id=row["id"],
            trigger=row["trigger"],
            categories=row["categories"],
            status=row["status"],
            started_at=_dt(row["started_at"]),
            requested_by=row.get("requested_by"),
        )

    async def finish_run(
        self,
        run_id: int,
        status: Literal["success", "failed"],
        fetched_count: int,
        inserted_count: int,
        error: str | None = None,
    ) -> None:
        await self._request(
            "PATCH",
            "/collect_runs",
            params={"id": f"eq.{run_id}"},
            json={
                "status": status,
                "fetched_count": fetched_count,
                "inserted_count": inserted_count,
                "error": error,
                "finished_at": datetime.now(KST).isoformat(),
            },
            prefer="return=minimal",
        )

    async def last_manual_run_started_at(self) -> datetime | None:
        rows = await self._request(
            "GET",
            "/collect_runs",
            params={"select": "started_at", "trigger": "eq.manual", "order": "started_at.desc", "limit": "1"},
        )
        return _dt(rows[0]["started_at"]) if rows else None

    # ---------------------------------------------------------------- 프로필·피드백
    async def get_profile(self, user_id: str) -> ProfileRecord | None:
        rows = await self._request("GET", "/profiles", params={"select": "*", "user_id": f"eq.{user_id}"})
        return _profile_record(rows[0]) if rows else None

    async def save_profile(self, profile: ProfileRecord) -> ProfileRecord:
        rows = await self._request(
            "POST",
            "/profiles",
            params={"on_conflict": "user_id"},
            json={
                "user_id": profile.user_id,
                "company_name": profile.company_name,
                "industries": profile.industries,
                "regions": profile.regions,
                "min_price": profile.min_price,
                "max_price": profile.max_price,
                "keywords": profile.keywords,
                "consent_at": profile.consent_at.isoformat(),
            },
            prefer="resolution=merge-duplicates,return=representation",
        )
        return _profile_record(rows[0])

    async def add_feedback(self, user_id: str | None, rating: int, message: str, page: str | None) -> int:
        rows = await self._request(
            "POST",
            "/feedbacks",
            json={"user_id": user_id, "rating": rating, "message": message, "page": page},
            prefer="return=representation",
        )
        return rows[0]["id"]

    async def delete_user(self, user_id: str) -> None:
        # Auth 계정을 지우면 DB 외래키가 profiles·recommendations는 삭제, 나머지 연결은 null로 정리한다.
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout) as client:
                response = await client.delete(f"{self._auth_admin}/users/{user_id}", headers=self._headers)
        except httpx.HTTPError as exc:
            raise RepositoryError(f"Supabase Auth 계정 삭제 연결 실패: {type(exc).__name__}") from None
        if response.status_code == 404:  # 이미 삭제된 계정
            return
        if response.status_code >= 400:
            raise RepositoryError(f"Supabase Auth 계정 삭제 오류 {response.status_code}: {response.text[:300]}")

    # ---------------------------------------------------------------- HTTP
    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self._send(method, path, **kwargs)
        return response.json() if response.content else None

    async def _send(
        self,
        method: str,
        path: str,
        *,
        params: Any = None,
        json: Any = None,
        prefer: str | None = None,
        allow_status: set[int] | None = None,
    ) -> httpx.Response:
        headers = dict(self._headers)
        if prefer:
            headers["Prefer"] = prefer
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout) as client:
                response = await client.request(method, self._base + path, params=params, json=json, headers=headers)
        except httpx.HTTPError as exc:
            raise RepositoryError(f"Supabase {method} {path} 연결 실패: {type(exc).__name__}") from None
        if response.status_code >= 400 and response.status_code not in (allow_status or set()):
            raise RepositoryError(f"Supabase {method} {path} 오류 {response.status_code}: {response.text[:300]}")
        return response


# -------------------------------------------------------------------- 변환
def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value).astimezone(KST) if value else None


def _bid_row(bid: Bid) -> dict[str, Any]:
    # 컬럼명이 Bid 필드명과 같다 (raw 포함). collected_at·updated_at은 DB가 관리한다.
    return bid.model_dump(mode="json")


def _bid_record(row: dict[str, Any]) -> BidRecord:
    summary_row = row.get("bid_summaries")
    if isinstance(summary_row, list):  # 관계 해석 방식에 따라 배열로 올 수 있다
        summary_row = summary_row[0] if summary_row else None
    summary = (
        BidSummaryRecord(
            summary=summary_row["summary"],
            qualifications=summary_row.get("qualifications"),
            required_documents=summary_row.get("required_documents") or [],
            provider=summary_row["provider"],
            model=summary_row["model"],
        )
        if summary_row
        else None
    )
    bid = Bid(
        bid_ntce_no=row["bid_ntce_no"],
        bid_ntce_ord=row["bid_ntce_ord"],
        category=row["category"],
        bid_ntce_nm=row["bid_ntce_nm"],
        ntce_instt_nm=row.get("ntce_instt_nm"),
        dminstt_nm=row.get("dminstt_nm"),
        presmpt_prce=row.get("presmpt_prce"),
        bid_ntce_dt=_dt(row.get("bid_ntce_dt")),
        bid_clse_dt=_dt(row.get("bid_clse_dt")),
        openg_dt=_dt(row.get("openg_dt")),
        bid_ntce_dtl_url=row.get("bid_ntce_dtl_url"),
        raw=row.get("raw") or {},
    )
    return BidRecord(id=row["id"], bid=bid, summary=summary)


def _settings_record(row: dict[str, Any]) -> SettingsRecord:
    return SettingsRecord(
        categories=row["categories"],
        num_rows=row["num_rows"],
        updated_at=_dt(row["updated_at"]),
        updated_by=row.get("updated_by"),
    )


def _profile_record(row: dict[str, Any]) -> ProfileRecord:
    return ProfileRecord(
        user_id=row["user_id"],
        company_name=row.get("company_name"),
        industries=row.get("industries") or [],
        regions=row.get("regions") or [],
        min_price=row.get("min_price"),
        max_price=row.get("max_price"),
        keywords=row.get("keywords") or [],
        consent_at=_dt(row["consent_at"]),
    )


def _clean(value: str) -> str:
    """PostgREST 필터 문법을 깨는 문자를 제거한다."""
    return "".join(ch for ch in value if ch not in '*"\\(),')


def _filter_params(f: BidFilter) -> list[tuple[str, str]]:
    params: list[tuple[str, str]] = []
    if f.category:
        params.append(("category", f"eq.{f.category}"))
    if f.q and (q := _clean(f.q).strip()):
        params.append(("bid_ntce_nm", f"ilike.*{q}*"))
    if f.institution and (inst := _clean(f.institution).strip()):
        params.append(("or", f'(ntce_instt_nm.ilike."*{inst}*",dminstt_nm.ilike."*{inst}*")'))
    if f.min_price is not None:
        params.append(("presmpt_prce", f"gte.{f.min_price}"))
    if f.max_price is not None:
        params.append(("presmpt_prce", f"lte.{f.max_price}"))
    if f.closing_from:
        params.append(("bid_clse_dt", f"gte.{datetime.combine(f.closing_from, time.min, KST).isoformat()}"))
    if f.closing_to:
        params.append(("bid_clse_dt", f"lte.{datetime.combine(f.closing_to, time.max, KST).isoformat()}"))
    return params


def _total_from_content_range(value: str | None) -> int:
    # 예: "0-19/57", 결과가 없으면 "*/0"
    if not value or "/" not in value:
        return 0
    total = value.rsplit("/", 1)[1]
    return int(total) if total.isdigit() else 0
