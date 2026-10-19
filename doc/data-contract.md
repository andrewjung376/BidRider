# 데이터·API 계약서

팀장(Backend/AI)과 팀원(Frontend/Data)이 함께 지키는 계약이다.
- **DB 스키마**: 팀원이 이 문서대로 마이그레이션 SQL과 RLS를 작성한다 (`supabase/migrations/`).
- **API**: 팀장이 이 문서대로 FastAPI 엔드포인트를 구현하고, 팀원은 이 응답 형식에 맞춰 UI를 만든다. API가 준비되기 전에는 아래 응답 예시를 가짜 데이터로 쓴다.
- **변경 절차**: 계약을 바꿀 때는 이 문서를 고치는 PR을 먼저 올리고, 상대 역할의 리뷰를 받은 뒤 병합한다.

버전: v1.2 (2026-10-19) — D3 API 확정: Agent 채팅, 적합도 추천, 👍/👎 (3.4)

이전: v1.1 `DELETE /api/me` 추가 (#21) / v1 최초 작성

---

## 1. 공통 규칙
| 항목 | 규칙 |
|---|---|
| 시간대 | 나라장터 시각은 KST. DB는 `timestamptz`로 저장하고, API는 ISO 8601 + `+09:00`로 응답 (예: `2026-10-15T18:30:40+09:00`) |
| 금액 | 원 단위 정수 (`bigint`). 값이 없으면 `null` (외자 공고는 추정가격이 비어 있음) |
| 업무 구분 | `용역`, `공사`, `물품`, `외자` 네 값만 사용 (한글 그대로 저장·전송) |
| 이름 규칙 | DB 컬럼과 API 필드는 `snake_case`. 나라장터 원본 필드는 그대로 `raw`(jsonb)에 보관 |
| DB 접근 | **web은 DB를 직접 읽거나 쓰지 않는다.** 데이터는 모두 FastAPI(`/api/*`)를 거친다. web의 Supabase 클라이언트는 **로그인(Auth)에만** 쓴다 |
| 인증 | 로그인이 필요한 API는 `Authorization: Bearer <Supabase access_token>` 헤더를 보낸다. FastAPI가 Supabase Auth로 토큰을 검증한다 |
| 서버 키 | `SUPABASE_SERVICE_ROLE_KEY`는 api에서만 쓴다. web 코드와 브라우저에 절대 넣지 않는다 |

---

## 2. DB 스키마 (Supabase PostgreSQL)

### 2.1 확장
- `pg_trgm`: 한국어 공고명 부분 검색용. PostgreSQL 기본 FTS는 한국어 형태소 분석을 지원하지 않으므로, 키워드 검색은 `ILIKE` + 트라이그램 인덱스로 한다.

### 2.2 `bids` — 입찰공고
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | `bigint` | PK, `generated always as identity` | |
| `bid_ntce_no` | `text` | not null | 공고번호 (예: `R26BK01774288`) |
| `bid_ntce_ord` | `text` | not null, default `'000'` | 차수 |
| `category` | `text` | not null, check (`용역`,`공사`,`물품`,`외자`) | 업무 구분 |
| `bid_ntce_nm` | `text` | not null | 공고명 |
| `ntce_instt_nm` | `text` | | 공고기관 |
| `dminstt_nm` | `text` | | 수요기관 |
| `presmpt_prce` | `bigint` | | 추정가격 |
| `bid_ntce_dt` | `timestamptz` | | 공고게시일시 |
| `bid_clse_dt` | `timestamptz` | | 입찰마감일시 |
| `openg_dt` | `timestamptz` | | 개찰일시 |
| `bid_ntce_dtl_url` | `text` | | 나라장터 상세 URL |
| `raw` | `jsonb` | not null | 원본 응답 항목 전체 |
| `collected_at` | `timestamptz` | not null, default `now()` | 처음 수집한 시각 |
| `updated_at` | `timestamptz` | not null, default `now()` | 마지막으로 갱신한 시각 |

- 유니크: `(bid_ntce_no, bid_ntce_ord)` — 수집 시 이 키로 upsert한다.
- 인덱스: `bid_ntce_dt desc`, `category`, `bid_clse_dt`, `bid_ntce_nm gin_trgm_ops`

### 2.3 `bid_summaries` — AI 요약 (FR-04)
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `bid_id` | `bigint` | PK, FK → `bids.id` on delete cascade | 공고당 1개 |
| `summary` | `text` | not null | 3줄 요약 |
| `qualifications` | `text` | | 참가자격 요약 (원문에 없으면 `null`) |
| `required_documents` | `jsonb` | not null, default `'[]'` | 제출서류 목록 (문자열 배열) |
| `provider` | `text` | not null | `claude` 또는 `openai` |
| `model` | `text` | not null | 예: `claude-haiku-5-5` |
| `created_at` | `timestamptz` | not null, default `now()` | |

### 2.4 `collect_settings` — 수집 설정 (FR-14, 서비스 전체 1행)
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | `smallint` | PK, default `1`, check (`id = 1`) | 항상 1행만 |
| `categories` | `text[]` | not null, default `'{용역}'`, 1개 이상, 각 값은 업무 구분 4개 중 하나 | 수집 대상 업무 구분 |
| `num_rows` | `int` | not null, default `10`, check (1~100) | 업무 구분당 수집 건수 |
| `updated_by` | `uuid` | FK → `auth.users.id` on delete set null | 마지막 수정자 |
| `updated_at` | `timestamptz` | not null, default `now()` | |

- 마이그레이션에서 기본 1행(`id=1`)을 함께 넣는다.

### 2.5 `collect_runs` — 수집 실행 기록 (NFR-02, "지금 수집" 호출 간격 제한)
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | `bigint` | PK, identity | |
| `trigger` | `text` | not null, check (`cron`,`manual`) | 실행 경로 |
| `categories` | `text[]` | not null | 실행한 업무 구분 |
| `status` | `text` | not null, check (`running`,`success`,`failed`) | |
| `fetched_count` | `int` | not null, default `0` | API에서 받은 건수 |
| `inserted_count` | `int` | not null, default `0` | 새로 저장한 건수 |
| `error` | `text` | | 실패 메시지 (인증키 마스킹된 값) |
| `requested_by` | `uuid` | FK → `auth.users.id` on delete set null | 수동 실행한 사용자 |
| `started_at` | `timestamptz` | not null, default `now()` | |
| `finished_at` | `timestamptz` | | |

### 2.6 `profiles` — 회사 프로필 (FR-05, Long-term Memory)
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `user_id` | `uuid` | PK, FK → `auth.users.id` on delete cascade | |
| `company_name` | `text` | | 회사명 (선택) |
| `industries` | `text[]` | not null, default `'{}'` | 업종 (예: `소프트웨어 개발`) |
| `regions` | `text[]` | not null, default `'{}'` | 지역 (예: `서울`) |
| `min_price` | `bigint` | | 관심 금액 하한 |
| `max_price` | `bigint` | | 관심 금액 상한 |
| `keywords` | `text[]` | not null, default `'{}'` | 관심 키워드 |
| `consent_at` | `timestamptz` | not null | 개인정보 수집·이용 동의 시각 (NFR-05) |
| `created_at` | `timestamptz` | not null, default `now()` | |
| `updated_at` | `timestamptz` | not null, default `now()` | |

### 2.7 `recommendations` — 적합도 추천과 피드백 (FR-06·08, D3)
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `user_id` | `uuid` | PK(복합), FK → `auth.users.id` on delete cascade | |
| `bid_id` | `bigint` | PK(복합), FK → `bids.id` on delete cascade | |
| `score` | `int` | not null, check (0~100) | 적합도 점수 |
| `reason` | `text` | not null | 판단 근거 |
| `feedback` | `smallint` | check (`-1`, `1`) | 👎 = -1, 👍 = 1, 미응답 = `null` |
| `model` | `text` | not null | |
| `created_at` / `updated_at` | `timestamptz` | not null, default `now()` | |

### 2.8 `feedbacks` — 사용자 테스트 피드백 (FR-11)
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | `bigint` | PK, identity | |
| `user_id` | `uuid` | FK → `auth.users.id` on delete set null | 비로그인 제출 허용 |
| `rating` | `smallint` | not null, check (1~5) | 만족도 |
| `message` | `text` | not null | 의견 |
| `page` | `text` | | 제출한 화면 경로 |
| `created_at` | `timestamptz` | not null, default `now()` | |

### 2.9 RLS
- **모든 테이블에 RLS를 켠다.** api는 service role 키로 접근하므로 RLS를 우회한다. 아래 정책은 키가 잘못 노출되거나 web이 실수로 직접 접근하는 경우를 막는 방어선이다.

| 테이블 | anon | authenticated |
|---|---|---|
| `bids`, `bid_summaries` | select 허용 (공공데이터) | select 허용 |
| `collect_settings`, `collect_runs` | 없음 | 없음 (api 경유) |
| `profiles`, `recommendations` | 없음 | 본인 행(`user_id = auth.uid()`)만 select·insert·update·delete |
| `feedbacks` | 없음 | 없음 (api 경유) |

---

## 3. API (FastAPI, 기본 경로 `/api`)

### 3.1 공통
- 형식: JSON (UTF-8)
- 오류 응답: `{"detail": "메시지"}` (FastAPI 기본 형식)

| 상태 코드 | 의미 |
|---|---|
| 400 / 422 | 요청 값 오류 |
| 401 | 로그인 필요 또는 토큰 오류 |
| 404 | 대상 없음 |
| 429 | 호출 간격 제한 (`Retry-After` 헤더에 남은 초) |
| 502 | 공공데이터포털 또는 LLM 호출 실패 |

### 3.2 `Bid` 객체
```json
{
  "id": 123,
  "bid_ntce_no": "R26BK01774288",
  "bid_ntce_ord": "000",
  "category": "용역",
  "bid_ntce_nm": "서창1분구(1블럭) 하수관로 정비사업 GIS DB 구축 용역",
  "ntce_instt_nm": "전남광주통합특별시 광주청사",
  "dminstt_nm": "전남광주통합특별시 광주청사",
  "presmpt_prce": 164118182,
  "bid_ntce_dt": "2026-10-15T18:30:40+09:00",
  "bid_clse_dt": "2026-10-27T10:00:00+09:00",
  "openg_dt": "2026-10-27T11:00:00+09:00",
  "bid_ntce_dtl_url": "https://www.g2b.go.kr/...",
  "summary": {
    "summary": "...\n...\n...",
    "qualifications": "...",
    "required_documents": ["입찰참가신청서", "..."],
    "ai_generated": true,
    "model": "claude-haiku-5-5"
  }
}
```
- `summary`는 요약이 아직 없으면 `null`이다. 값이 있으면 UI에 **"AI 생성" 배지와 원문 링크**를 함께 표시한다 (NFR-04).
- 요약은 **수집 직후** 생성된다 (Cron·"지금 수집" 모두). "지금 수집"은 응답을 오래 붙잡지 않도록 요약 시간을 짧게 두므로, 일부 공고는 `summary`가 `null`로 남았다가 다음 수집 때 채워질 수 있다. 근거는 나라장터 API 필드뿐이라 `required_documents`는 대부분 빈 목록이다.
- 위 예시의 `bid_clse_dt`, `openg_dt`, `dminstt_nm`, `bid_ntce_dtl_url`, `summary` 값은 형식을 보여 주기 위한 예시다.

### 3.3 엔드포인트 (D2 범위)
| 메서드·경로 | 인증 | 설명 |
|---|---|---|
| `GET /api/health` | 없음 | 상태 확인 (구현 완료) |
| `GET /api/bids` | 없음 | 공고 목록 (FR-03) |
| `GET /api/bids/{id}` | 없음 | 공고 상세 |
| `POST /api/collect` | 필요 | "지금 수집" (FR-02) |
| `GET /api/settings` | 없음 | 수집 설정 조회 (FR-14) |
| `PUT /api/settings` | 필요 | 수집 설정 변경 (FR-14) |
| `GET /api/me/profile` | 필요 | 내 프로필 조회 (FR-05) |
| `PUT /api/me/profile` | 필요 | 내 프로필 저장 (FR-05) |
| `DELETE /api/me` | 필요 | 탈퇴: 계정과 개인 데이터 삭제 (NFR-05) |
| `POST /api/feedback` | 선택 | 피드백 제출 (FR-11) |
| `GET /api/cron/collect` | `CRON_SECRET` | Vercel Cron 전용, web에서 호출하지 않음 |

#### `GET /api/bids`
쿼리 파라미터 (모두 선택)

| 이름 | 예시 | 설명 |
|---|---|---|
| `category` | `용역` | 업무 구분 |
| `q` | `GIS` | 공고명 키워드 (부분 일치) |
| `institution` | `광주` | 공고기관·수요기관 부분 일치 |
| `min_price`, `max_price` | `10000000` | 추정가격 범위 |
| `closing_from`, `closing_to` | `2026-10-16` | 입찰마감일 범위 (KST 날짜) |
| `page` | `1` | 기본 1 |
| `size` | `20` | 기본 20, 최대 100 |

정렬은 `bid_ntce_dt` 내림차순(최신순) 고정.

응답
```json
{ "items": [Bid], "total": 57, "page": 1, "size": 20 }
```

#### `GET /api/bids/{id}`
`Bid`에 첨부파일 목록을 더해 응답한다. 없으면 404.
```json
{ "...Bid 필드": "...", "attachments": [{ "name": "공고서.hwp", "url": "https://..." }] }
```

#### `POST /api/collect`
요청 (모두 선택. 생략하면 저장된 수집 설정을 따른다)
```json
{ "categories": ["용역", "공사"], "num_rows": 10 }
```
응답
```json
{ "run_id": 42, "status": "success", "categories": ["용역", "공사"], "fetched_count": 20, "inserted_count": 7 }
```
- 호출 간격 제한: 마지막 수동 수집 후 **60초** 안에 다시 호출하면 429.

#### `GET /api/settings` · `PUT /api/settings`
```json
{ "categories": ["용역"], "num_rows": 10, "updated_at": "2026-10-16T09:00:00+09:00" }
```
- `PUT` 요청 본문은 `categories`(1개 이상)와 `num_rows`(1~100). 응답은 `GET`과 같다.

#### `GET /api/me/profile` · `PUT /api/me/profile`
```json
{
  "company_name": "예시소프트",
  "industries": ["소프트웨어 개발"],
  "regions": ["서울"],
  "min_price": 10000000,
  "max_price": 100000000,
  "keywords": ["GIS", "데이터베이스"],
  "consent_at": "2026-10-16T09:00:00+09:00"
}
```
- `GET`: 프로필이 없으면 404 (UI는 프로필 작성 화면으로 안내).
- `PUT` 요청 본문은 위에서 `consent_at`을 빼고 **`"consent": true`** 를 넣는다. 처음 저장할 때 `consent`가 `true`가 아니면 400.

#### `POST /api/feedback`
```json
{ "rating": 4, "message": "목록이 보기 편해요", "page": "/bids" }
```
응답: `201` `{ "id": 7 }`

#### `DELETE /api/me`
요청 본문 없음. 응답: **`204`** (본문 없음)
- 로그인한 사용자의 **Supabase Auth 계정을 삭제**한다. DB 외래키에 따라 함께 처리된다 (2장).

| 테이블 | 처리 |
|---|---|
| `profiles`, `recommendations` | 삭제 (`on delete cascade`) |
| `feedbacks.user_id`, `collect_runs.requested_by`, `collect_settings.updated_by` | `null`로 연결 해제 (`on delete set null`). 피드백 내용과 수집 기록은 익명으로 남는다 |

- 이미 삭제된 계정이면(인증 서버 404) 그대로 `204`를 돌려준다.
- 성공 후 web은 `supabase.auth.signOut()`으로 브라우저 세션을 정리한다. 삭제된 계정의 기존 토큰은 다음 api 호출부터 401이다.
- 되돌릴 수 없으므로 UI는 삭제 전 확인 단계를 둔다.

### 3.4 D3 API (Agent·추천)
| 메서드·경로 | 인증 | 설명 |
|---|---|---|
| `POST /api/agent/chat` | 필요 | 자연어 검색 Agent (FR-07, RAG FR-09) |
| `GET /api/recommendations` | 필요 | 내 프로필 기준 적합도 추천 (FR-06) |
| `POST /api/recommendations/{bid_id}/feedback` | 필요 | 추천 👍/👎 (FR-08) |

- 세 API 모두 LLM을 호출하므로 비용·남용 방지를 위해 **로그인이 필요**하다.
- 사용자별 호출 간격 제한(429)은 현재 없다. 비용은 로그인 필수와 Anthropic 사용 한도로 관리한다. 추가할 경우 3.1과 같은 `429` + `Retry-After` 형식을 쓴다.
- LLM 호출이 포함되어 응답이 **최대 약 30초** 걸릴 수 있다. UI는 진행 중 표시를 하고, 요청 제한 시간은 **60초 이상**으로 둔다.
- 응답의 AI 생성 내용(`answer`, `reason`)에는 `ai_generated: true`가 붙는다. UI는 "AI 생성" 배지와 함께 표시하고, 공고는 원문 링크를 함께 보여 준다 (NFR-04).

#### `POST /api/agent/chat`
대화 기록은 서버에 저장하지 않는다. web이 이전 대화를 `history`로 함께 보낸다.

요청
```json
{
  "message": "서울 SW 개발 1억 이하, 이번 주 마감 공고 찾아줘",
  "history": [
    { "role": "user", "content": "GIS 관련 공고 있어?" },
    { "role": "assistant", "content": "최근 공고 중 GIS 관련 공고는 2건입니다. ..." }
  ]
}
```
- `message`: 1~1000자
- `history`: 최대 10개 (오래된 것부터 잘라서 보낸다). `role`은 `user` 또는 `assistant`, `content`는 1~4000자

응답 `200`
```json
{
  "answer": "조건에 맞는 공고는 2건입니다.
1. 서창1분구 하수관로 정비사업 GIS DB 구축 용역 (R26BK01774288-000) — 마감 10/27
2. ...",
  "bids": [Bid],
  "tool_calls": [
    { "name": "search_bids", "args": { "category": "용역", "q": "SW", "max_price": 100000000, "closing_to": "2026-10-25" }, "result_count": 2 }
  ],
  "ai_generated": true,
  "model": "claude-sonnet-5-5"
}
```
- `answer`: 줄바꿈이 있는 일반 텍스트 (마크다운 아님). 공고를 언급할 때 `공고번호-차수`를 함께 적는다.
- `bids`: 답변이 근거로 쓴 공고 (최대 10건, 언급 순서). `Bid` 형식은 3.2와 같다. UI는 답변 아래에 공고 카드로 보여 주고 `/bids/{id}`로 연결한다.
- `tool_calls`: Agent가 실행한 도구와 인자 (발표·디버깅용, UI 표시는 선택). 도구는 `search_bids`(3.3 `GET /api/bids`와 같은 필터), `get_bid_detail`.
- 로그인 사용자의 **회사 프로필이 있으면 답변에 반영**한다 (Long-term Memory). 프로필이 없어도 동작한다.
- 오류: `401` 로그인 필요, `422` 입력값 오류, `502` LLM 호출 실패 (`detail`에 사유)

#### `GET /api/recommendations`
내 프로필로 **아직 마감되지 않은 최신 공고**의 적합도를 평가해 점수순으로 돌려준다.

쿼리 파라미터: `limit` (기본 10, 최대 20)

응답 `200`
```json
{
  "items": [
    {
      "bid": Bid,
      "score": 87,
      "reason": "관심 업종(소프트웨어 개발)과 지역(서울)이 일치하고, 추정가격이 관심 금액 범위 안이다.",
      "feedback": null,
      "ai_generated": true,
      "model": "claude-haiku-5-5"
    }
  ],
  "pending": 3
}
```
- 정렬: `score` 내림차순, 같으면 공고게시일시 최신순
- 후보는 입찰마감일이 오늘(KST) 이후인 공고다. **마감일이 없는(`null`) 공고는 제외**한다.
- 평가 결과는 `recommendations`에 저장해 두고 다시 계산하지 않는다. **새 공고와, 프로필을 바꾼 뒤의 공고만** 새로 평가한다. 다시 평가해도 **👍/👎는 유지**한다.
- 프로필을 바꾼 뒤 아직 다시 평가하지 않은 추천은 `items`에 넣지 않는다 (이전 프로필 기준 점수를 보여 주지 않음).
- 한 번 요청에서 새로 평가하는 공고 수와 시간에는 제한이 있다. 아직 평가하지 못한 후보 수가 `pending`이다. `pending > 0`이면 UI는 "더 불러오기"(같은 요청 다시 호출)를 보여 줄 수 있다.
- `items`는 매번 **지금까지 평가된 전체 목록**(점수순, `limit` 이내)이다. "더 불러오기" 후에도 UI는 목록을 통째로 바꾼다.
- 👍/👎 이력은 **다음 평가에 반영**한다 (Long-term Memory). 이미 매긴 점수는 바뀌지 않는다.
- 오류: `401` 로그인 필요, **`404` 프로필 없음** (UI는 프로필 작성으로 안내), `502` LLM 호출 실패

#### `POST /api/recommendations/{bid_id}/feedback`
요청
```json
{ "feedback": 1 }
```
- `1` = 👍, `-1` = 👎, `null` = 취소

응답 `200`
```json
{ "bid_id": 123, "feedback": 1 }
```
- 오류: `401` 로그인 필요, `404` 내 추천 목록에 없는 공고, `422` 값 오류

---

## 4. 환경 변수
| 이름 | 사용처 | 설명 |
|---|---|---|
| `SUPABASE_URL` | api | |
| `SUPABASE_SERVICE_ROLE_KEY` | api | 서버 전용 |
| `SUPABASE_ANON_KEY` | api | 토큰 검증 호출용 |
| `NEXT_PUBLIC_SUPABASE_URL` | web | 로그인용 |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | web | 로그인용 (공개 가능 키) |
| `API_BASE_URL` | web (서버 측) | rewrites 대상. 로컬 `http://127.0.0.1:8000`, 배포 시 api 프로젝트 URL |
