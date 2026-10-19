"""Bid Agent: 자연어 공고 검색 (FR-07) + 검색 결과 근거 답변 (RAG, FR-09).

- 도구는 서비스 함수(search_bids, get_bid_detail)를 그대로 쓴다 (PRD 5.2).
- 로그인 사용자의 회사 프로필을 프롬프트에 넣어 개인화한다 (Long-term Memory).
- 답변이 언급한 공고(공고번호)만 응답의 bids로 돌려준다.
"""

import json
from datetime import date, datetime
from typing import Any

from pydantic import ValidationError

from app.koneps.models import KST
from app.llm.base import AgentResult, LLMProvider, ToolSpec
from app.repository.base import BidRepository, ProfileRecord
from app.schemas import BidFilter, BidOut, ChatOut, ChatTurn, ToolCallOut
from app.services import bids as bid_service

MAX_RESULTS = 10
MAX_BIDS_IN_ANSWER = 10
WEEKDAYS = "월화수목금토일"

TOOLS = [
    ToolSpec(
        name="search_bids",
        description=(
            "BidRadar에 수집된 나라장터 입찰공고를 조건으로 검색한다. 공고게시일시 최신순. "
            "조건은 모두 선택이며, 사용자가 말한 조건만 넣는다. 결과가 없으면 조건을 줄여 다시 검색할 수 있다."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["용역", "공사", "물품", "외자"], "description": "업무 구분"},
                "q": {"type": "string", "description": "공고명 키워드 (부분 일치, 한 단어 권장. 예: GIS, 설계, 소프트웨어)"},
                "institution": {"type": "string", "description": "공고기관·수요기관 이름 일부 (예: 서울, 광주, 조달청)"},
                "min_price": {"type": "integer", "description": "추정가격 하한(원)"},
                "max_price": {"type": "integer", "description": "추정가격 상한(원). 예: 1억 = 100000000"},
                "closing_from": {"type": "string", "description": "입찰마감일 시작 (YYYY-MM-DD, KST)"},
                "closing_to": {"type": "string", "description": "입찰마감일 끝 (YYYY-MM-DD, KST)"},
                "size": {"type": "integer", "description": f"가져올 건수 (1~{MAX_RESULTS}, 기본 {MAX_RESULTS})"},
            },
            "additionalProperties": False,
        },
    ),
    ToolSpec(
        name="get_bid_detail",
        description="공고 id로 상세 정보(AI 요약, 참가자격, 첨부파일명)를 가져온다. 검색 결과의 id를 쓴다.",
        input_schema={
            "type": "object",
            "properties": {"id": {"type": "integer", "description": "search_bids 결과의 id"}},
            "required": ["id"],
            "additionalProperties": False,
        },
    ),
]


def build_system_prompt(today: date, profile: ProfileRecord | None) -> str:
    lines = [
        "당신은 BidRadar의 입찰공고 검색 도우미다. 사용자가 나라장터 입찰공고를 찾고 이해하도록 돕는다.",
        "",
        "규칙:",
        "- 공고 정보는 반드시 도구(search_bids, get_bid_detail)로 확인한 내용만 말한다. 도구 결과에 없는 공고·금액·조건은 만들지 않는다.",
        "- 공고를 언급할 때는 공고명과 함께 공고번호-차수(예: R26BK01774288-000)를 적는다.",
        "- 조건에 맞는 공고가 없으면 없다고 말하고, 조건을 넓혀 볼 방법을 제안한다.",
        "- 한국어 일반 텍스트로 짧게 답한다. 마크다운 기호(#, **, 표)는 쓰지 않는다. 목록은 '1.' 형식 줄바꿈으로 쓴다.",
        "- 입찰 참여 판단에 필요한 정보(마감일, 추정가격, 지역·업종 제한)를 우선 알려 주고, 최종 확인은 나라장터 원문에서 하도록 안내한다.",
        "- 입찰공고와 관련 없는 요청에는 BidRadar는 입찰공고 검색을 돕는다고 짧게 안내한다.",
        "",
        f"오늘 날짜: {today.isoformat()} ({WEEKDAYS[today.weekday()]}요일, KST). "
        "'이번 주'는 오늘부터 이번 주 일요일까지, '다음 주'는 다음 주 월~일요일로 계산해 closing_from·closing_to를 정한다.",
        "금액 표현: 1억 = 100000000, 5천만 = 50000000.",
    ]
    if profile:
        lines += [
            "",
            "사용자의 회사 프로필 (검색 조건이 모호할 때 참고하고, 답변에서 프로필과 맞는 점을 짚어 준다):",
            f"- 업종: {', '.join(profile.industries) or '미입력'}",
            f"- 지역: {', '.join(profile.regions) or '미입력'}",
            f"- 관심 금액: {_price(profile.min_price)} ~ {_price(profile.max_price)}",
            f"- 관심 키워드: {', '.join(profile.keywords) or '미입력'}",
        ]
    return "\n".join(lines)


async def chat(
    repo: BidRepository,
    llm: LLMProvider,
    message: str,
    history: list[ChatTurn],
    *,
    user_id: str | None,
    now: datetime | None = None,
) -> ChatOut:
    today = (now or datetime.now(KST)).date()
    profile = await repo.get_profile(user_id) if user_id else None
    seen: dict[int, BidOut] = {}

    async def execute(name: str, args: dict[str, Any]) -> tuple[str, int | None]:
        args = dict(args)  # tool_calls 기록용 원본은 건드리지 않는다
        if name == "search_bids":
            size = max(1, min(int(args.pop("size", MAX_RESULTS) or MAX_RESULTS), MAX_RESULTS))
            try:
                filters = BidFilter(**args)
            except ValidationError as exc:
                raise ValueError(f"검색 조건 형식 오류: {exc.errors()[0]['msg']}") from None
            result = await bid_service.search_bids(repo, filters, 1, size)
            for bid in result.items:
                seen[bid.id] = bid
            payload = {"total": result.total, "items": [_brief(b) for b in result.items]}
            return json.dumps(payload, ensure_ascii=False), result.total
        if name == "get_bid_detail":
            detail = await bid_service.get_bid_detail(repo, int(args["id"]))
            if detail is None:
                raise ValueError("해당 id의 공고가 없습니다.")
            seen[detail.id] = BidOut(**detail.model_dump(exclude={"attachments"}))
            data = _brief(detail) | {
                "qualifications": detail.summary.qualifications if detail.summary else None,
                "attachments": [a.name for a in detail.attachments],
            }
            return json.dumps(data, ensure_ascii=False), 1
        raise ValueError(f"알 수 없는 도구: {name}")

    messages = [{"role": t.role, "content": t.content} for t in history] + [{"role": "user", "content": message}]
    result: AgentResult = await llm.run_agent(
        system=build_system_prompt(today, profile), messages=messages, tools=TOOLS, execute=execute
    )
    return ChatOut(
        answer=result.text,
        bids=_cited(result.text, seen),
        tool_calls=[ToolCallOut(name=c.name, args=c.args, result_count=c.result_count) for c in result.tool_calls],
        model=result.model or llm.model,
    )


def _cited(answer: str, seen: dict[int, BidOut]) -> list[BidOut]:
    """답변이 공고번호로 언급한 공고만, 언급한 순서대로."""
    positions = []
    for bid in seen.values():
        pos = answer.find(bid.bid_ntce_no)
        if pos >= 0:
            positions.append((pos, bid))
    return [bid for _, bid in sorted(positions, key=lambda x: x[0])][:MAX_BIDS_IN_ANSWER]


def _brief(bid: BidOut) -> dict[str, Any]:
    return {
        "id": bid.id,
        "공고번호": f"{bid.bid_ntce_no}-{bid.bid_ntce_ord}",
        "업무구분": bid.category,
        "공고명": bid.bid_ntce_nm,
        "공고기관": bid.ntce_instt_nm,
        "수요기관": bid.dminstt_nm,
        "추정가격": bid.presmpt_prce,
        "게시": _fmt(bid.bid_ntce_dt),
        "입찰마감": _fmt(bid.bid_clse_dt),
        "요약": bid.summary.summary if bid.summary else None,
    }


def _fmt(dt: datetime | None) -> str | None:
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M") if dt else None


def _price(value: int | None) -> str:
    return f"{value:,}원" if value is not None else "제한 없음"
