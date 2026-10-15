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

### 팀원
- Supabase 프로젝트 `bidradar` 생성 (리전 `ap-northeast-2` 서울, Free 플랜, ref `dboyvetydfgqzrpmobrk`)
- #4 Supabase 스키마와 RLS 마이그레이션 완료 → PR #10 병합
  - `supabase/migrations/20261015160032_init_schema.sql`: 계약서 2장 기준 테이블 7개, 제약·인덱스, `pg_trgm`(`extensions` 스키마), `collect_settings` 기본 1행
  - RLS: `bids`·`bid_summaries` 공개 조회, `profiles`·`recommendations` 본인 행만, 나머지 3개는 api 경유 전용
  - 계약서 외 추가: `updated_at` 자동 갱신 트리거, `recommendations.bid_id` 인덱스
  - 검증: 컬럼·제약·인덱스·RLS·기본 행이 계약서와 일치. Supabase advisor는 INFO만 (정책 없는 테이블 3개는 의도한 상태)
- 팀원 전용 Python 가상환경(`.venv`, 3.13.5) 생성, `api/requirements-dev.txt` 설치. api 테스트 10건 통과(실호출 1건 skip)

#### 결정 사항
| 결정 | 이유 |
|---|---|
| 마이그레이션 파일명을 원격 이력 버전(`20261015160032`)에 맞춤 | Supabase 커넥터로 적용한 버전과 로컬 파일이 어긋나지 않게 해서, 나중에 CLI(`db push`)를 써도 중복 적용되지 않게 함 |
| 팀원은 팀장과 다른 가상환경 사용 | 같은 `.venv`에서 동시에 패키지 설치·테스트를 하면 충돌할 수 있음 |

#### 다음 할 일
- #5 Next.js 뼈대와 API 프록시 → 이후 #6~#9
- 사용자 요청 필요: Google OAuth 클라이언트 생성·Supabase 등록(#7), Supabase 키를 `.env`·`web/.env.local`에 입력, Vercel 프로젝트 2개 생성
