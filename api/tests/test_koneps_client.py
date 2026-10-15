"""KonepsClient 단위 테스트 (실제 API를 호출하지 않는다).

실호출 확인은 RUN_LIVE=1 일 때만 test_live_fetch_latest가 실행한다.
"""

import os
from datetime import datetime, timedelta

import httpx
import pytest

from app.koneps.client import KST, KonepsClient, KonepsError

BASE = "https://example.test/BidPublicInfoService"
KEY = "abc+def/ghi=="


def _item(i: int) -> dict:
    dt = datetime(2026, 10, 14, 9, 0) + timedelta(minutes=i)
    return {
        "bidNtceNo": f"R26BK{i:08d}",
        "bidNtceOrd": "000",
        "bidNtceNm": f"공고 {i}",
        "ntceInsttNm": "기관",
        "presmptPrce": "1000000",
        "bidNtceDt": dt.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _fake_api(total: int, calls: list[httpx.Request]) -> httpx.MockTransport:
    """공고게시일시 오름차순으로 total건을 페이지 단위로 돌려주는 가짜 API."""
    all_items = [_item(i) for i in range(total)]

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        rows = int(request.url.params["numOfRows"])
        page = int(request.url.params["pageNo"])
        chunk = all_items[(page - 1) * rows : page * rows]
        body = {"items": chunk, "numOfRows": rows, "pageNo": page, "totalCount": total}
        return httpx.Response(200, json={"response": {"header": {"resultCode": "00", "resultMsg": "정상"}, "body": body}})

    return httpx.MockTransport(handler)


@pytest.mark.anyio
async def test_returns_latest_items_newest_first() -> None:
    calls: list[httpx.Request] = []
    client = KonepsClient(KEY, BASE, transport=_fake_api(total=25, calls=calls))

    bids = await client.fetch_latest("용역", 10)

    assert [b.bid_ntce_no for b in bids] == [f"R26BK{i:08d}" for i in range(24, 14, -1)]
    # 25건 / 10건 → 1페이지(건수 확인) + 2·3페이지(마지막 페이지가 5건뿐이라 앞 페이지까지)
    assert [c.url.params["pageNo"] for c in calls] == ["1", "2", "3"]
    assert all(c.url.path.endswith("/getBidPblancListInfoServc") for c in calls)


@pytest.mark.anyio
async def test_single_page_uses_first_call_only() -> None:
    calls: list[httpx.Request] = []
    client = KonepsClient(KEY, BASE, transport=_fake_api(total=7, calls=calls))

    bids = await client.fetch_latest("공사", 10)

    assert len(bids) == 7
    assert bids[0].bid_ntce_no == "R26BK00000006"
    assert bids[0].category == "공사"
    assert len(calls) == 1
    assert calls[0].url.path.endswith("/getBidPblancListInfoCnstwk")


@pytest.mark.anyio
async def test_empty_result() -> None:
    client = KonepsClient(KEY, BASE, transport=_fake_api(total=0, calls=[]))
    assert await client.fetch_latest() == []


@pytest.mark.anyio
async def test_encoding_key_is_not_double_encoded() -> None:
    calls: list[httpx.Request] = []
    encoded = "abc%2Bdef%2Fghi%3D%3D"
    client = KonepsClient(encoded, BASE, transport=_fake_api(total=1, calls=calls))

    await client.fetch_latest()

    assert calls[0].url.params["serviceKey"] == KEY


@pytest.mark.anyio
async def test_query_params() -> None:
    calls: list[httpx.Request] = []
    client = KonepsClient(KEY, BASE, transport=_fake_api(total=1, calls=calls))
    now = datetime(2026, 10, 15, 10, 30, tzinfo=KST)

    await client.fetch_latest(lookback_days=3, now=now)

    params = calls[0].url.params
    assert params["inqryDiv"] == "1"
    assert params["inqryBgnDt"] == "202610121030"
    assert params["inqryEndDt"] == "202610151030"
    assert params["type"] == "json"


@pytest.mark.anyio
async def test_error_header_raises() -> None:
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, json={"response": {"header": {"resultCode": "20", "resultMsg": "ACCESS DENIED"}}})
    )
    with pytest.raises(KonepsError, match="20"):
        await KonepsClient(KEY, BASE, transport=transport).fetch_latest()


@pytest.mark.anyio
async def test_xml_error_masks_service_key() -> None:
    xml = f"<OpenAPI_ServiceResponse><returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR {KEY}</returnAuthMsg></OpenAPI_ServiceResponse>"
    transport = httpx.MockTransport(lambda r: httpx.Response(200, text=xml))

    with pytest.raises(KonepsError) as exc_info:
        await KonepsClient(KEY, BASE, transport=transport).fetch_latest()

    assert KEY not in str(exc_info.value)
    assert "SERVICE_KEY_IS_NOT_REGISTERED_ERROR" in str(exc_info.value)


def test_invalid_arguments() -> None:
    with pytest.raises(KonepsError):
        KonepsClient("", BASE)


@pytest.mark.anyio
async def test_unknown_category() -> None:
    with pytest.raises(ValueError):
        await KonepsClient(KEY, BASE).fetch_latest("기타")


@pytest.mark.anyio
@pytest.mark.skipif(os.getenv("RUN_LIVE") != "1", reason="실호출은 RUN_LIVE=1일 때만")
async def test_live_fetch_latest() -> None:
    from app.config import get_settings

    settings = get_settings()
    bids = await KonepsClient(settings.data_go_kr_service_key, settings.koneps_base_url).fetch_latest("용역", 10)

    assert 0 < len(bids) <= 10
    dts = [b.bid_ntce_dt for b in bids]
    assert dts == sorted(dts, reverse=True)
