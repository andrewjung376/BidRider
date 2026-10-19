# 진행 기록

일자별로 한 일, 결정 사항, 다음 할 일을 기록한다.

## D1 — 2026-10-15 (목)

### 한 일
- 기획서(`doc/prd.md`)와 나라장터 API 조사(`doc/api-research.md`) 작성 후 커밋
- `.gitignore` 정리: `doc/` 제외 항목 삭제(문서도 제출물), `.env.*`·Node/Next.js·Vercel·캐시 항목 추가, `.env.example`은 예외
- Python 가상환경(`.venv`, Python 3.13.5) 생성
- `api/` 뼈대: FastAPI 앱, 헬스체크(`/api/health`), 환경 변수 설정(`app/config.py`), pytest, `vercel.json`(리전 `icn1`)
- `.env.example`, `README.md` 초안 작성
- 작업 방식: `feature/*` 브랜치 + PR + 상호 리뷰

### 결정 사항
| 결정 | 이유 |
|---|---|
| **FastMCP는 외부 연동 층(Should)으로만 사용**. Agent는 LLM SDK tool calling으로 서비스 함수를 직접 호출 | FastMCP는 project.md 필수 요건이 아니고, 서버리스에서 `/mcp` 동작이 불확실함. Must 기능이 FastMCP에 의존하지 않게 함 |
| **로그인을 매직 링크에서 Google 로그인으로 변경** | Supabase Free 기본 이메일 발송이 프로젝트 전체 시간당 2통이라 테스터 5명이 로그인할 수 없음 |
| Vercel 함수 리전 `icn1`, Supabase 리전 서울 | Hobby는 단일 리전만 가능(기본 미국). 공공데이터포털 해외 IP 차단 가능성 대응 |
| `web`→`api` 호출은 Next.js rewrites 프록시 | 두 Vercel 프로젝트 간 CORS 회피 |
| 테스터에게 Production URL만 공유 | Preview 배포는 기본적으로 Vercel 로그인 필요 |

### 나라장터 수집 클라이언트 PoC (`api/app/koneps`)
- 인증키 발급 후 로컬 실호출 성공: 용역·공사·물품·외자 4개 업무구분 모두 `resultCode 00`
- **발견**: 응답이 공고게시일시 오름차순 → 최신 N건은 마지막 페이지에 있음. 1페이지로 `totalCount` 확인 후 마지막 페이지(나머지가 있으면 앞 페이지까지) 조회하도록 구현
- Encoding/Decoding 인증키 모두 처리, 오류 메시지에서 인증키 마스킹, XML 오류 응답 처리
- 테스트: 단위 테스트 10건(가짜 API) + 실호출 테스트 1건(`RUN_LIVE=1`일 때만) 통과
- 로컬 확인 명령: `cd api && python -m app.koneps 용역 10`

### 확인 필요
- Vercel Python 런타임이 `api/main.py`의 `app`을 진입점으로 인식하는지 (첫 배포 시 확인)
- Vercel Python 버전(3.12) vs 로컬 3.13 차이로 인한 문제 여부
- 공공데이터포털 참고문서(docx)로 오퍼레이션·파라미터 검증

### 다음 할 일
- 팀장: 서비스 함수(`collect_latest` 등) 정의, Supabase 저장 연동, LLMProvider 인터페이스
- 팀원: Supabase 프로젝트(서울)·스키마·RLS·Google 로그인 설정, Next.js 스캐폴드, Vercel 프로젝트 2개 연결
- 공통: 테스터 5명 이상 모집

## D2 — 2026-10-16 (금)

### 팀장
- 데이터·API 계약서(`doc/data-contract.md`) v1 작성: DB 스키마 7개 테이블과 RLS, D2 범위 API 형식
  - 결정: web은 DB에 직접 접근하지 않고 모든 데이터를 FastAPI로 주고받음 (Supabase 클라이언트는 로그인에만 사용)
  - 결정: 한국어 키워드 검색은 PostgreSQL 기본 FTS 대신 `pg_trgm` + `ILIKE` (기본 FTS는 한국어 형태소 미지원)
- 협업 방식: 팀원은 별도 clone(`BidRider-member`)에서 작업하고, GitHub 이슈와 PR로만 소통
- L4 공고 서비스·API (`feature/bid-service`)
  - `BidRepository` 인터페이스와 메모리 구현체 (L6에서 Supabase 구현체로 교체)
  - 서비스 함수(`app/services/bids.py`): `collect_latest`, `search_bids`, `get_bid_detail`, 수집 설정 조회·변경. API·Agent·FastMCP가 공통으로 호출
  - API: `GET /api/bids`, `GET /api/bids/{id}`, `POST /api/collect`(60초 간격 제한, 429), `GET·PUT /api/settings`, `GET /api/cron/collect`(`CRON_SECRET`)
  - 인증: Supabase Auth `/auth/v1/user`로 토큰 검증. Supabase·CRON 설정이 비어 있으면 503으로 거부 (안전한 기본값)
  - Vercel Cron: 매일 00:00 UTC(09:00 KST)
  - 나라장터 시각을 KST 시간대 포함 값으로 저장하도록 수정 (API 응답 `+09:00`)
  - 테스트 26건 통과(실호출 1건 skip). 로컬 서버에서 실제 수집 → 목록·상세·키워드 검색 확인
  - 확인: 공공데이터포털 응답이 호출당 수 초~십수 초 걸림 (Vercel 300초 제한 안에서는 문제없음)
- L6 Supabase 저장 연동 (`feature/supabase-repo`)
  - `SupabaseBidRepository`: 새 라이브러리 없이 httpx로 PostgREST 호출. 공고 upsert(`on_conflict`)와 신규 건수 계산, 필터·전체 건수(`count=exact`)·요약 함께 조회, 수집 설정·실행 기록, 프로필, 피드백
  - DB 시각(UTC)을 KST로 바꿔 응답 (`+09:00`)
  - API 추가: `GET·PUT /api/me/profile`(처음 저장 시 동의 필수, 최초 동의 시각 유지), `POST /api/feedback`(비로그인 허용)
  - 저장소 자동 선택: Supabase 설정이 있으면 Supabase, 없으면 메모리. 저장소 오류는 502 + 일반 메시지(상세는 서버 로그)
  - 키: publishable 키는 Supabase 커넥터로 조회해 `.env`에 입력, service role 키는 커넥터로 조회할 수 없어 사용자가 직접 입력
  - 테스트 35건 통과(실호출 2건 skip). 실제 Supabase에 용역 최신 10건 저장 → 재수집 시 신규 0건(중복 없음) → 목록·상세·키워드 검색 확인
- L5 LLM 제공자와 AI 요약 (`feature/llm-summary`, FR-04)
  - `LLMProvider` 인터페이스(`structured`)와 `ClaudeProvider`: SDK `messages.parse(output_format=Pydantic)`, effort `low`, 거절·잘림·API 오류를 `LLMError`로 변환. OpenAI는 미구현(설정 시 요약 생략)
  - 요약 서비스: 나라장터 필드 35개 + 첨부파일명을 근거로 3줄 요약·제한 조건·제출서류. 추측 금지, "~다"체, 없는 값 언급 금지, 첨부파일은 제출서류가 아님을 명시
  - 수집 직후 요약이 없는 공고를 동시 5건으로 요약 ("지금 수집" 25초, Cron 120초 제한). 요약 실패·시간 초과는 수집 결과에 영향 없음
  - 실측: Supabase의 기존 10건을 Claude Haiku 5.5로 요약 → 10건 성공, 12.5초 (건당 약 2.5~5초)
  - 프롬프트 개선 2회: ① 문체 혼용·"값 없음" 언급 → 통일·생략 지시 ② 첨부파일명을 제출서류로 분류 → 제외 지시
  - 한계: 상세 참가자격·제출서류는 첨부파일(HWP/PDF) 안에 있어 반영 못 함 (FR-13 범위 밖)
  - 테스트 47건 통과(실호출 2건 skip)
- PR #16(팀원 #6 UI) 리뷰 중 api 버그 발견·수정 (`feature/fix-page-range`)
  - 현상: 마지막 페이지를 넘는 `page` 요청 시 502. 원인: PostgREST가 범위 초과 offset에 416(`PGRST103`)을 주는데 처리하지 않음 (메모리 저장소 테스트로는 드러나지 않음)
  - 수정: 목록 조회에서만 416을 빈 목록 + 전체 건수로 처리. 테스트 2건 추가(총 49건), 실제 Supabase로 `page=5` → 200·빈 목록 확인

### 팀원
- Supabase 프로젝트 `bidradar` 생성 (리전 `ap-northeast-2` 서울, Free 플랜, ref `dboyvetydfgqzrpmobrk`)
- #4 Supabase 스키마와 RLS 마이그레이션 완료 → PR #10 병합
  - `supabase/migrations/20261015160032_init_schema.sql`: 계약서 2장 기준 테이블 7개, 제약·인덱스, `pg_trgm`(`extensions` 스키마), `collect_settings` 기본 1행
  - RLS: `bids`·`bid_summaries` 공개 조회, `profiles`·`recommendations` 본인 행만, 나머지 3개는 api 경유 전용
  - 계약서 외 추가: `updated_at` 자동 갱신 트리거, `recommendations.bid_id` 인덱스
  - 검증: 컬럼·제약·인덱스·RLS·기본 행이 계약서와 일치. Supabase advisor는 INFO만 (정책 없는 테이블 3개는 의도한 상태)
- 팀원 전용 Python 가상환경(`.venv`, 3.13.5) 생성, `api/requirements-dev.txt` 설치. api 테스트 10건 통과(실호출 1건 skip)
- #5 Next.js 뼈대와 API 프록시 → PR #13 병합
  - `web/`: Next.js 16.3.8(App Router, TypeScript, Tailwind), `next.config.ts` rewrites로 `/api/*` → `API_BASE_URL`, `web/vercel.json` 리전 `icn1`
  - 홈 화면에 `/api/health` 연결 상태 표시(실패 시 api 실행 안내), `.env.example`에 web 변수, README에 web 실행 방법
- #6 공고 목록·상세·필터 UI → PR #16 병합, 리뷰 후속 PR #18 병합
  - `/bids` 목록(필터: 업무 구분·키워드·기관·금액·마감일, 주소창 쿼리로 관리, 페이지 이동), `/bids/[id]` 상세(AI 요약 카드·"AI 생성" 배지·참고용 안내·원문 링크·첨부파일)
  - 금액 `null` → `-`, KST 날짜, 마감 D-day 배지, 로딩·결과 없음·오류·404 화면, 모바일 375px 확인
  - 한글 글꼴 Pretendard(dynamic subset) 적용 (#13 리뷰 참고사항)
  - 리뷰 후속: 마지막 페이지를 넘으면 "해당 페이지에 공고가 없습니다" + 1페이지 링크, 최소 금액 > 최대 금액 안내
- #9 피드백 폼과 테스터 모집 안내문 → PR #19 병합 (리뷰 2회 변경 요청 반영)
  - `/feedback`: 만족도 1~5, 의견(2000자), 보던 화면 경로(`?from=`)를 함께 저장, 비로그인 제출, 상단·하단 "의견 보내기" 링크
  - `doc/user-test.md`: 5명 이상(목표 7명) 모집 계획·안내문, 테스트 시나리오 6단계, 결과 정리 양식
  - 리뷰 반영: `?from=` 오픈 리다이렉트 — 1차 `/\evil.com`(역슬래시), 2차 `/.//evil.com`(URL 정리 후 `//`). 검사 함수를 `web/lib/safe-path.ts`로 분리하고 `npm test`(node:test 27건) 추가
  - 확인용 피드백 1건 제출 후 삭제 (`feedbacks` 0건 유지)
- #7 Google 로그인·회사 프로필·개인정보 동의 → PR #20 병합
  - `@supabase/supabase-js`(로그인 전용, PKCE), 상단 로그인·로그아웃, `apiFetch`(로그인 상태면 Bearer 토큰, 피드백 폼에도 적용)
  - `/profile`: 404면 작성 모드, 업종·지역·키워드·금액 범위, 처음 저장 시 개인정보 수집·이용 동의 필수(항목·목적·보유 기간)
  - 실제 Google 로그인 → 복귀 → 동의·저장(`PUT` 200, `consent_at` 기록) → 다시 열기 → 로그아웃 확인 (사용자와 함께)
- #8 수집 설정 화면과 지금 수집 → PR #22 병합
  - `/settings`: 업무 구분 다중 선택(1개 이상)·건수 1~100 저장, "지금 수집"은 화면에서 고른 업무 구분으로 수집
  - 진행 중 표시·경과 시간, 90초 제한, 받은·새로 저장 건수, 429 `Retry-After` 카운트다운, 502 사유 표시
  - 서버 api 호출에 `connection()` (빌드 시점 렌더링 방지), 상단 메뉴에 "수집 설정"(휴대폰 폭 줄바꿈 방지)
  - 실제 수동 수집 3건 모두 `success`, `bids` 10 → 17건, 수집 설정은 확인 후 `{용역}`·10건으로 복구
- 리뷰 후속(#22 참고사항): `doc/user-test.md` 5단계에 "수집 설정은 바꾸지 말고 지금 수집만" 안내, 테스트 후 설정 값 확인 항목 추가
- 사용자 작업 지원: Google OAuth 클라이언트·Supabase Google 로그인 설정, `web/.env.local` 작성 방법 안내와 확인(키 값은 보지 않고 형식만 확인)

#### 결정 사항
| 결정 | 이유 |
|---|---|
| 마이그레이션 파일명을 원격 이력 버전(`20261015160032`)에 맞춤 | Supabase 커넥터로 적용한 버전과 로컬 파일이 어긋나지 않게 해서, 나중에 CLI(`db push`)를 써도 중복 적용되지 않게 함 |
| 팀원은 팀장과 다른 가상환경 사용 | 같은 `.venv`에서 동시에 패키지 설치·테스트를 하면 충돌할 수 있음 |
| 목록·상세는 서버 컴포넌트에서 `API_BASE_URL`로 직접 호출, 브라우저 요청만 rewrites 프록시 | 필터를 주소창 쿼리로 관리해 뒤로 가기·링크 공유가 되고, web은 여전히 DB에 직접 접근하지 않음 (계약서 1장) |
| 한글 글꼴 Pretendard(dynamic subset) | 한국어 UI에서 숫자·금액 가독성이 좋고, 화면에 쓰인 글자 파일만 내려받아 모바일에서도 가벼움 |
| 로그인은 supabase-js 브라우저 클라이언트만 사용 (`@supabase/ssr` 미사용) | 공고 화면은 로그인이 필요 없고 Supabase는 로그인에만 쓰므로 서버 세션 처리 없이 가장 단순하게 구성 |
| 사용자 경로 검사는 `parseSafePath` 하나로 모으고 자동 테스트로 고정 | 같은 검사에서 우회 경로를 두 번 놓쳤음. 이후 다른 화면도 이 함수를 재사용 (팀장 요청) |
| "지금 수집" 제한 시간 90초, 성공 후 60초 버튼 비활성화 | 공공데이터포털 응답이 업무 구분당 수 초~십수 초(팀장 요청 최소 60초), api 수동 수집 간격(60초)과 맞춤 |

#### 다음 할 일
- 팀장 #21(탈퇴·데이터 삭제 API)이 준비되면 프로필 화면의 "삭제 요청은 의견 보내기로" 안내를 삭제 버튼으로 교체 (팀원 이슈로 요청 예정)
- D3(10/19): 채팅 UI(FR-07), AI 배지, 추천 👍/👎(FR-08), 1차 배포 확인
- 테스터 모집 시작(`doc/user-test.md` 안내문), 10/19까지 5명 이상 확정
- 사용자 요청 필요: Vercel 프로젝트 2개 생성·배포, Vercel `web` 환경 변수(`NEXT_PUBLIC_SUPABASE_*`, `API_BASE_URL`) 후 재배포, Supabase Site URL·Redirect URLs에 Production URL 추가, Google OAuth 앱 게시

## D3 — 2026-10-19 (월)

### 팀장
- #21 탈퇴·데이터 삭제 API (NFR-05, `feature/delete-me`)
  - 계약서 v1.1: `DELETE /api/me` → 204
  - 결정: **Supabase Auth 계정 삭제 한 번으로 처리**. 마이그레이션의 외래키가 `profiles`·`recommendations`는 삭제(cascade), `feedbacks`·`collect_runs`·`collect_settings`의 사용자 연결은 `null`(set null)로 정리하므로 테이블별 삭제 코드가 필요 없고 누락 위험도 없음
  - 이미 삭제된 계정(인증 서버 404)도 204 (반복 호출 안전)
  - 확인: 존재하지 않는 계정 ID로 실제 관리자 삭제 호출 → 인증 통과·404 처리, 기존 데이터 변화 없음. 실제 계정 삭제는 하지 않음
  - 테스트 54건 통과(실호출 2건 skip)
- 계약서 v1.2 (D3 API: Agent 채팅·적합도 추천·👍/👎) PR #26 — 팀원 리뷰 대기
- **1차 배포 (Vercel)**
  - 프로젝트: `bidradar-api`(FastAPI, 루트 `api`), `bidradar-web`(Next.js, 루트 `web`), 둘 다 GitHub `main` 연결(병합 시 자동 배포), 함수 리전 `icn1`
  - 주소: 서비스 **https://bidradar-web-mocha.vercel.app** (`bidradar-web` 이름이 이미 사용 중이라 `-mocha`가 붙음), api https://bidradar-api.vercel.app
  - 생성 과정: Vercel 커넥터는 프로젝트 생성 권한이 없어(403) 실패 → 사용자가 Vercel CLI 로그인과 **Vercel GitHub App 설치(BidRider만 허용)** → 팀장이 CLI(`vercel api`)로 프로젝트 생성·배포
  - 환경 변수: 비밀이 아닌 값(모델명, Supabase URL, publishable 키, `API_BASE_URL`)은 팀장이 등록, **비밀 값 4개(`DATA_GO_KR_SERVICE_KEY`, `ANTHROPIC_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `CRON_SECRET`)는 사용자가 Sensitive로 직접 입력**. 배포용 Anthropic 키와 Supabase secret 키는 로컬과 분리해 새로 발급
  - 확인: 배포 리전 `icn1`, Cron `/api/cron/collect` 매일 09:00 KST 등록, api·web 모든 화면 200, 프록시 정상, 인증 보호(토큰 없음 401, Cron 비밀 없음 401), 응답 0.1~1.6초
  - **Cron 수동 실행(사용자가 Vercel에서 Run)**: 10건 수집 3초 + 새 공고 10건 Claude 요약 약 8초 → **Vercel 서울 리전에서 공공데이터포털 정상 호출(해외 IP 차단 위험 해소)**, `bids` 17 → 27건
  - Production Google 로그인: 사용자가 Supabase Site URL·Redirect URLs 설정 후 확인
  - 참고: Preview 환경에는 비밀 변수 일부가 없음 (테스터는 Production만 사용)
- **Agent·추천 구현** (`feature/agent-recommend`, 계약서 v1.2 PR #26 기준)
  - `POST /api/agent/chat` (FR-07·09): Claude Sonnet 5.5 도구 호출 루프(최대 3단계, 마지막 단계는 도구 없이 답변), 도구 `search_bids`·`get_bid_detail`은 기존 서비스 함수 재사용(PRD 5.2), 오늘 날짜(요일)·로그인 사용자 프로필을 시스템 프롬프트에 넣음, 답변이 공고번호로 언급한 공고만 `bids`로 반환. 거절(refusal) 시 서버 측 대체 모델(`fallbacks: "default"`) 사용
  - `GET /api/recommendations` (FR-06): 마감 전 최신 공고 30건 후보, Claude Haiku 5.5로 점수·근거 평가(동시 5건, 한 번에 10건, 25초 제한) → `recommendations` 저장, 새 공고·프로필 변경 후 공고만 재평가, 남은 후보는 `pending`
  - `POST /api/recommendations/{bid_id}/feedback` (FR-08): 👍/👎 저장, 재평가해도 유지, 다음 평가 프롬프트에 👍·👎 공고명을 넣음 (Long-term Memory)
  - 테스트 68건 통과(실호출 2건 skip). 실제 Claude 확인: Agent "이번 주 마감 설계 용역" → `closing_from/to`를 이번 주(10/19~10/25)로 계산해 5건 인용(9.4초), "1억 이하 서울·경기" → 기관별 2회 검색(6.6초) / 추천 10건 평가 5.2초 (실제 공고를 메모리 저장소에 복사해 평가, 실제 계정 데이터에는 쓰지 않음)

- 팀원 PR 리뷰·병합: #27(탈퇴 버튼), #32(채팅 UI), #33(추천 UI), #34·#35(사용자 테스트 문서·결과). #35 결과를 Supabase로 직접 대조(계정·프로필·추천 73건·👍/👎 0건·의견 6건 평균 4.67·공고 47건 모두 일치)
  - 실수와 재발 방지: #32 병합 때 `--delete-branch`로 #33의 기준 브랜치를 지워 #33이 자동으로 닫힘 → 기준 브랜치를 원래 커밋으로 복원해 다시 열고 `main`으로 변경해 복구. 이후 쌓인 PR은 **기준 브랜치를 먼저 바꾼 뒤** 아래 PR 브랜치를 삭제 (#34·#35에 적용)
- 테스트용 Google 계정 Production 탈퇴 확인 (`auth.users` 1개, 남은 연결 데이터 0건)
### 팀원
- #24 팀장 PR(탈퇴·데이터 삭제 API, 계약서 v1.1) 리뷰 — 승인 의견
  - 실제 Supabase에서 `auth.users`를 참조하는 외래키 5개(`profiles`·`recommendations` cascade, `feedbacks`·`collect_runs`·`collect_settings` set null)가 PR 설명과 일치함을 확인, PR 브랜치 `pytest` 54건 통과
  - supabase-js `signOut`이 계정 삭제 후 401·403·404를 무시하고 브라우저 세션을 지우는 것을 코드로 확인
- #25 프로필 화면 탈퇴(계정 삭제) 버튼 → PR #27 병합
  - "탈퇴" 입력 후 계정 삭제 활성화, `DELETE /api/me` → `signOut` → 홈 완료 안내, 동의 문구에 "피드백은 익명으로 남음"·보유 기간 수정
  - 사용자 테스트 계정으로 탈퇴 → 같은 계정 재로그인 시 프로필 없음(404) 확인. 프로필 저장 후 탈퇴는 UI로 확인하지 못해, 실제 DB에서 가짜 계정 트랜잭션 테스트(전부 롤백)로 cascade·익명 처리 확인
- #26 팀장 PR(계약서 v1.2, Agent·추천) 리뷰 — 승인 의견과 확인 요청 4건(더 불러오기 `items` 범위, 재평가 시 👍/👎 유지, 마감일 없는 공고, 채팅 429) → 팀장이 계약서에 모두 반영 후 병합
- #30 AI 공고 검색 채팅 UI → PR #32 병합
  - `/chat`: 답변(AI 생성 배지)·근거 공고 카드, `history` 최근 10개·내용 4000자 이내 전송, 예시 질문, 검색 조건 보기, 90초 제한
  - 공고 카드 공용화(`components/bid-card.tsx`), 상단 메뉴 휴대폰 폭 가로 스크롤
  - 로컬 web을 Production api에 연결해 확인: 질문 1에 5건 인용·프로필 반영, 이어지는 질문에서 앞 대화 기억
- #31 적합도 추천·👍/👎 UI → PR #33 병합 (#32 위에 쌓은 PR)
  - `/recommendations`: 점수·근거·공고 카드, 👍/👎 토글(다시 누르면 취소), "더 불러오기"(목록 전체 교체, 불러오는 동안 기존 목록 유지), 404 프로필 안내
  - Production api로 확인: 10건 → 더 불러오기 20건, 👍 저장·새로고침 유지·취소
- `doc/user-test.md`: 접속 주소(`https://bidradar-web-mocha.vercel.app`), 시나리오 4단계 AI 검색·5단계 맞춤 추천 추가 (PR #34)
- **사용자 테스트 진행 (Production)** — 결과는 `doc/user-test.md` 4장
  - 테스터 5명(T1~T4 + 탈퇴한 T5, 모두 PC). 테스트 시간에 쓰인 운영 계정 T0은 진행자 본인 사용이라 집계에서 제외. 의견 6건, 평균 만족도 4.67/5, 테스트 중 api 오류 로그 0건
  - 탈퇴하면 프로필·추천은 삭제되고 피드백 작성자는 비워지므로, 탈퇴 계정 활동은 Vercel api 로그(1시간 보관)로 대조. 작성자 없는 의견 1건은 탈퇴 74초 뒤 홈에서 제출되어 탈퇴한 T5의 것으로 추정
  - 사용: 프로필 저장 3명, AI 검색 1명(1건, 이어지는 질문 없음), 추천 평가 2명(50건) + 프로필 없음 안내 2명(실제 동작 확인), 지금 수집 2명(공고 27 → 47건), 탈퇴 1명
  - 개선 후보: ① 지금 수집 신규 0건 안내가 눈에 띄지 않음(T4 의견) ② 👍/👎를 누른 사람 0명(탈퇴 계정 포함, 관찰) ③ 프로필 저장 후 추천으로 가는 링크(선택). 보류: 가입·탈퇴 메일(Supabase 메일 한도)

#### 결정 사항
| 결정 | 이유 |
|---|---|
| 채팅 `history`의 각 내용을 4000자로 잘라 보냄 | 계약서상 `content`는 최대 4000자인데 답변 길이는 제한이 없어, 긴 답변을 그대로 보내면 다음 질문이 422로 끊길 수 있음 |
| #31을 #32 위에 쌓은 PR로 올림 | 공고 카드·경과 시간 훅·타입을 공유해, 리뷰를 기다리는 동안 이어서 작업하면서 PR마다 해당 변경만 보이게 함 |
| 사용자 테스트 결과는 서버 기록으로 확인한 것만 적음 | 테스터 명단은 저장소에 두지 않으므로 계정 생성 순서로 번호를 붙이고, 로그인 없는 조회(목록·상세)는 사람별로 구분할 수 없어 표에서 뺌 |
| 탈퇴 계정은 DB 대신 api 로그로 확인하고, 작성자 없는 의견은 "추정"으로 표시 | 탈퇴 시 프로필·추천이 삭제되고 피드백 작성자가 비워져 DB만으로는 활동을 알 수 없음. 로그인 없이 제출한 사람과 구분할 방법이 없어 단정하지 않음 |

#### 다음 할 일
- 테스터 직군·소요 시간은 미확인으로 기록 (기기는 모두 PC)
- 10/21 반영 후보: 지금 수집 신규 0건 안내 강화, 👍/👎 눈에 띄게(버튼 크기·설명), (선택) 프로필 저장 후 "맞춤 추천 보기" 링크
- README 사용자 테스트 결과, 발표 자료·시연 영상 (D5)

## 마감 — 2026-10-20 (화) 10:00로 변경

### 팀장
- **제출 마감이 10/21에서 10/20 10:00으로 앞당겨짐** → D5(피드백 반영·README·발표) 일정을 10/19 밤~10/20 오전으로 당김
- 사용자 테스트 피드백 반영을 팀원 이슈 #36으로 등록 (지금 수집 신규 0건 안내, 👍/👎 강조, 프로필 저장 후 추천 링크, 09:00까지 PR)
- `README.md` 완성: 서비스 주소, 문제 정의·해결 방식, 주요 기능, 역할·협업 방식, 기술 스택과 근거(계획 대비 변경: FastMCP·n8n·OpenAI 제외), 아키텍처, 필수 기술 요소 4개 구현 위치, 프롬프트 설계, AI 윤리, 사용자 테스트 결과, 실행·테스트·배포 방법
- 발표 자료 `doc/presentation.md`(Marp 15장) → `doc/presentation.pdf`: 문제 정의, 해결 방식, 아키텍처, AI 활용 3장, 기술 결정 근거, 실측 개선, 협업, 사용자 테스트, 피드백 반영, 한계
- 시연 영상 순서 `doc/demo-script.md` (장면 9개, 약 3~4분, 시연용 프로필 예시) — 녹화·업로드는 사용자
- #36 → 팀원 PR #38 리뷰·병합 (마감 전 배포 확인): 신규 0건 안내 상자, 👍/👎 글자 라벨·질문·설명, 프로필 저장 후 추천 링크. README·발표 자료의 피드백 반영 표를 "반영 완료"로 갱신하고 PDF 재생성
