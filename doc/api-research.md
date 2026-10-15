# 나라장터 입찰공고 API 조사

조사일: 2026-10-15

## 1. 대상 API

**조달청_나라장터 입찰공고정보서비스** (공공데이터포털 데이터번호 **15129394**, 영문명 BidPublicInfoService)

- 상세 페이지: https://www.data.go.kr/data/15129394/openapi.do
- 포털 검색어: "나라장터 입찰공고정보서비스" 또는 `15129394` ("입찰공고"만으로는 찾기 어려움)

## 2. 공식 페이지에서 확인한 내용
| 항목 | 내용 |
|---|---|
| 제공기관 | 조달청 |
| 제공 내용 | 물품·용역·공사·외자 입찰공고 목록과 상세정보, 기초금액, 면허제한, 참가가능지역, 변경이력 |
| 갱신 주기 | 실시간 |
| 데이터 포맷 | JSON, XML (REST) |
| 활용신청 승인 | 개발·운영 단계 모두 자동승인 (심의 없음) |
| 일일 트래픽 | 개발계정 1,000건. 운영계정은 활용사례 등록 후 증설 신청 가능 |
| 이용허락범위 | 제한 없음 |
| 등록일 / 최종수정일 | 2024-07-02 / 2026-06-29 |
| 참고문서 | 조달청_OpenAPI참고자료_나라장터_입찰공고정보서비스_1.2.docx |
| 주의 | 업무구분(물품·용역·공사·외자)별로 오퍼레이션이 나뉘므로 공고의 업무구분에 맞는 오퍼레이션을 사용해야 함 |

## 3. 비공식 자료에서 확인한 내용
> 서드파티 문서 기준 항목이다. ✅ 표시는 **2026-10-15 로컬(국내망) 실호출로 확인**한 것이고, 나머지는 참고문서(docx)로 검증이 필요하다.

- ✅ **호출 주소**: `https://apis.data.go.kr/1230000/ad/BidPublicInfoService`
- ✅ **오퍼레이션** (4개 업무구분 모두 실호출 성공)

| 업무구분 | 오퍼레이션 |
|---|---|
| 용역 | `getBidPblancListInfoServc` |
| 공사 | `getBidPblancListInfoCnstwk` |
| 물품 | `getBidPblancListInfoThng` |
| 외자 | `getBidPblancListInfoFrgcpt` |

  - 서비스 전체 오퍼레이션은 25개. 키워드·금액 검색용 `...PPSSrch` 변형도 있다 (예: `getBidPblancListInfoServcPPSSrch`).
- **요청 파라미터**
  - ✅ `serviceKey`: 인증키
  - ✅ `numOfRows`, `pageNo`: 페이지 크기와 번호 (최대 999는 미확인)
  - ✅ `type=json`: JSON 응답
  - ✅ `inqryDiv=1`: 공고게시일시 기준 (3 = 변경일시 기준은 미확인)
  - ✅ `inqryBgnDt`, `inqryEndDt`: 조회 기간 (`YYYYMMDDHHMM`)
- **조회 기간 제한**: 호출 1회당 약 1개월 (미확인)
- ✅ **응답 구조**: `response.header.resultCode`(정상 `"00"`), `response.body.totalCount`, `response.body.items`(배열)
- ✅ **정렬**: 응답은 **공고게시일시(`bidNtceDt`) 오름차순**이다. 최신 N건은 마지막 페이지에 있으므로, 1페이지로 `totalCount`를 확인한 뒤 마지막 페이지(나머지가 있으면 그 앞 페이지까지)를 조회한다.
- ✅ **응답 필드**: `bidNtceNo`(공고번호), `bidNtceOrd`(차수, 예 `"000"`), `bidNtceNm`(공고명), `ntceInsttNm`(공고기관), `dminsttNm`(수요기관), `presmptPrce`(추정가격, 문자열·외자는 빈 값), `bidNtceDt`(공고게시일시, `YYYY-MM-DD HH:MM:SS`), `bidClseDt`(입찰마감일시), `opengDt`(개찰일시), `bidNtceDtlUrl`(상세 URL). 이 밖에 첨부파일(`ntceSpecDocUrl1~10`, `ntceSpecFileNm1~10`), 지역·업종 제한 여부, 낙찰방법 등 100개 이상 필드가 있다.
- **오류**: `Code 20 (Access Denied)` = 활용신청 미승인 또는 인증키 오류 (미확인). 인증키 오류는 `type=json`이어도 XML(`OpenAPI_ServiceResponse`)로 올 수 있어 클라이언트에서 처리한다.
- **인증키**: Encoding 키(`%` 포함)와 Decoding 키(원본) 두 종류. 클라이언트는 어느 쪽을 넣어도 원본 키로 되돌려 사용한다.

## 4. PRD와 맞춰볼 점
- ✅ **최신 10건 수집 가능**: `inqryDiv=1`, 최근 3일, `numOfRows=10`으로 업무구분당 1~3회 호출 (오름차순 정렬 때문에 마지막 페이지 조회). 2026-10-15 기준 용역 공고는 하루 약 600건.
- **일일 1,000건 제한**: 하루 1회 수집(업무구분당 최대 3회, 4구분이면 최대 12회)은 충분. "지금 수집" 버튼에는 호출 간격 제한을 둔다.
- **수집 설정(FR-14)**: 업무구분마다 오퍼레이션이 다르므로 선택한 구분 수만큼 호출 (최대 4회).
- **`bids` 모델 키**: `bidNtceNo` + `bidNtceOrd`가 PRD의 "공고번호 + 차수"와 일치.
- **해외 IP 차단 가능성(미검증)**: 로컬(국내망) 호출은 정상. Vercel 함수(리전 `icn1`)에서의 호출은 첫 배포 때 확인.
- **"실시간"의 실제 지연**: 19:00경 호출 시 18:58 게시 공고까지 조회됨 → 지연은 수 분 이내로 보임.

## 5. 후속 작업
1. ✅ 포털에서 활용신청 → 인증키 발급 (자동승인)
2. ✅ 인증키는 `.env`에만 저장하고 `.gitignore`에 `.env` 포함. 채팅·커밋에 노출하지 않는다.
3. 참고문서(docx)로 3장의 미확인 항목 검증 후 이 문서 갱신
4. ✅ D1 PoC: 4개 업무구분 최신 공고 호출, 정렬·응답 지연 확인 (`api/app/koneps`). 해외 IP 차단 여부는 Vercel 배포 후 확인

## 출처
- [조달청_나라장터 입찰공고정보서비스 (data.go.kr 15129394)](https://www.data.go.kr/data/15129394/openapi.do)
- [mcp-kr-g2b (Glama)](https://glama.ai/mcp/servers/ChangooLee/mcp-kr-g2b)
- [opendata-kr/narajangteo-bid-mcp (GitHub)](https://github.com/opendata-kr/narajangteo-bid-mcp)
- [KONEPS Live Tender Matcher (Apify)](https://apify.com/byungwoongyoo/koneps-tender-feed)
- [Nara MCP Server README (Glama)](https://glama.ai/mcp/servers/@Datajang/mcp-narajangteo/blob/55133d2ce4f3687c60640271eac660bc31a43109/README.md)
