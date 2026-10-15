"""공고 AI 요약 (FR-04).

- 근거는 나라장터 API의 구조화된 필드뿐이다. 첨부파일(HWP/PDF) 본문은 범위 밖(FR-13)이다.
- 원문에 없는 내용은 만들지 않도록 지시하고, 출력은 Pydantic 스키마로 검증한다.
- 요약 실패는 수집 결과에 영향을 주지 않는다 (호출하는 쪽에서 실패를 기록만 한다).
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field

from app.koneps.models import Bid
from app.llm.base import LLMError, LLMProvider
from app.repository.base import BidRepository, BidSummaryRecord

logger = logging.getLogger("bidradar.summaries")

SYSTEM_PROMPT = """당신은 대한민국 공공조달(나라장터) 입찰공고를 중소기업 입찰 담당자에게 요약해 주는 도우미다.

규칙:
- 아래에 주어진 공고 필드만 근거로 쓴다. 필드에 없는 내용(자격 세부 조건, 서류 목록, 금액 등)은 추측하거나 만들지 않는다.
- 한국어로, 담당자가 참여 여부를 빨리 판단할 수 있게 쓴다. 문장은 "~다"체로 통일한다.
- 값이 없는 항목은 "없다", "확인되지 않는다"처럼 언급하지 말고 그냥 생략한다.
- summary: 정확히 3줄, 각 줄은 80자 안팎. 줄바꿈(\\n)으로 구분하고, 마크다운·글머리표 기호 없이 쓴다.
  1줄: 무엇을 하는 사업인지와 발주기관
  2줄: 금액과 일정(입찰마감, 개찰)
  3줄: 계약·낙찰 방법과 눈여겨볼 제한 조건
- qualifications: 지역제한, 업종제한, 공동수급, 참가자격 등록 마감 같은 제한 조건을 1~3문장으로 요약한다. 관련 필드가 하나도 없으면 null.
- required_documents: 입찰 참가자가 제출해야 한다고 필드에 분명히 적힌 서류명만 넣는다. 첨부파일(공고문, 과업지시서, 평가기준 등)은 발주기관이 제공하는 문서라 제출 서류가 아니므로 넣지 않는다. 확인되지 않으면 빈 목록.

용어:
- 추정가격: 부가세를 뺀 예정 계약 금액. 배정예산: 발주기관이 배정한 예산.
- 공동수급: 여러 업체가 공동으로 계약하는 방식. 지역제한: 특정 지역 업체만 참가 가능.
- 적격심사: 가격과 수행능력을 함께 평가해 낙찰자를 정함. PQ: 사전 자격심사.
"""

# 프롬프트에 넣을 필드 (나라장터 원본 필드명 → 한국어 라벨). 값이 빈 필드는 넣지 않는다.
FIELD_LABELS: dict[str, str] = {
    "bidNtceNm": "공고명",
    "ntceKindNm": "공고 종류",
    "ntceInsttNm": "공고기관",
    "dminsttNm": "수요기관",
    "srvceDivNm": "용역 구분",
    "pubPrcrmntClsfcNm": "공공조달 분류",
    "presmptPrce": "추정가격(원)",
    "asignBdgtAmt": "배정예산(원)",
    "VAT": "부가세(원)",
    "bidNtceDt": "공고게시일시",
    "bidBeginDt": "입찰개시일시",
    "bidClseDt": "입찰마감일시",
    "opengDt": "개찰일시",
    "opengPlce": "개찰장소",
    "bidQlfctRgstDt": "입찰참가자격 등록마감일시",
    "bidMethdNm": "입찰방식",
    "cntrctCnclsMthdNm": "계약체결방법",
    "sucsfbidMthdNm": "낙찰방법",
    "sucsfbidLwltRate": "낙찰하한율(%)",
    "cmmnSpldmdMethdNm": "공동수급방식",
    "rgnDutyJntcontrctRt": "지역의무 공동도급 비율(%)",
    "jntcontrctDutyRgnNm1": "공동도급 의무지역1",
    "jntcontrctDutyRgnNm2": "공동도급 의무지역2",
    "jntcontrctDutyRgnNm3": "공동도급 의무지역3",
    "rgnLmtBidLocplcJdgmBssNm": "지역제한 판단기준",
    "indstrytyLmtYn": "업종제한 여부",
    "prdctClsfcLmtYn": "물품분류제한 여부",
    "bidPrtcptLmtYn": "입찰참가제한 여부",
    "pqEvalYn": "PQ 심사 여부",
    "tpEvalYn": "기술평가 여부",
    "dsgntCmptYn": "지명경쟁 여부",
    "arsltCmptYn": "실적경쟁 여부",
    "intrbidYn": "국제입찰 여부",
    "reNtceYn": "재공고 여부",
    "chgNtceRsn": "변경공고 사유",
}


class SummaryDraft(BaseModel):
    summary: str = Field(description="정확히 3줄, 줄바꿈으로 구분")
    qualifications: str | None = Field(description="제한 조건 요약, 관련 필드가 없으면 null")
    required_documents: list[str] = Field(description="분명히 확인되는 제출 서류명만, 없으면 빈 목록")


@dataclass
class SummarizeResult:
    summarized: int = 0
    failed: int = 0
    timed_out: bool = False


def build_prompt(bid: Bid) -> str:
    raw = bid.raw or {}
    # 정규화된 Bid 필드를 우선 쓰고, 나머지는 원본 필드에서 가져온다.
    known = {
        "bidNtceNm": bid.bid_ntce_nm,
        "ntceInsttNm": bid.ntce_instt_nm,
        "dminsttNm": bid.dminstt_nm,
        "presmptPrce": bid.presmpt_prce,
        "bidNtceDt": _fmt(bid.bid_ntce_dt),
        "bidClseDt": _fmt(bid.bid_clse_dt),
        "opengDt": _fmt(bid.openg_dt),
    }
    lines = [f"- 업무 구분: {bid.category}"]
    for key, label in FIELD_LABELS.items():
        value = known[key] if key in known else raw.get(key)
        if value not in (None, ""):
            lines.append(f"- {label}: {value}")
    files = [raw.get(f"ntceSpecFileNm{i}") for i in range(1, 11)]
    files = [f for f in files if f]
    if files:
        lines.append(f"- 첨부파일명: {', '.join(files)}")
    return "다음 입찰공고를 규칙에 따라 요약하라.\n\n" + "\n".join(lines)


def _fmt(dt: datetime | None) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else None


async def summarize_bid(llm: LLMProvider, bid: Bid) -> BidSummaryRecord:
    draft = await llm.structured(system=SYSTEM_PROMPT, prompt=build_prompt(bid), output_type=SummaryDraft)
    summary = "\n".join(line.strip() for line in draft.summary.strip().splitlines() if line.strip())
    if not summary:
        raise LLMError("빈 요약")
    return BidSummaryRecord(
        summary=summary,
        qualifications=(draft.qualifications or "").strip() or None,
        required_documents=[d.strip() for d in draft.required_documents if d.strip()],
        provider=llm.provider,
        model=llm.model,
    )


async def summarize_missing(
    repo: BidRepository,
    llm: LLMProvider,
    *,
    limit: int = 20,
    concurrency: int = 5,
    timeout: float = 40.0,
) -> SummarizeResult:
    """요약이 없는 최신 공고를 동시에 요약해 저장한다. 제한 시간을 넘기면 끝난 것만 남긴다."""
    records = await repo.list_unsummarized(limit)
    result = SummarizeResult()
    semaphore = asyncio.Semaphore(concurrency)

    async def one(bid_id: int, bid: Bid) -> None:
        async with semaphore:
            try:
                summary = await summarize_bid(llm, bid)
                await repo.save_summary(bid_id, summary)
                result.summarized += 1
            except LLMError as exc:
                result.failed += 1
                logger.warning("요약 실패 bid_id=%s: %s", bid_id, exc)

    try:
        await asyncio.wait_for(asyncio.gather(*(one(r.id, r.bid) for r in records)), timeout)
    except TimeoutError:
        result.timed_out = True
        logger.warning("요약 제한 시간 %.0f초 초과: %d건 완료", timeout, result.summarized)
    return result
