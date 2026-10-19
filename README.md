# BidRadar (입찰레이더)

> 나라장터 입찰공고를 자동으로 모아 **AI가 요약**하고, 회사 프로필에 맞는 공고를 **추천**하며, **채팅으로 검색**하는 AI 서비스

| 구분 | 주소 |
|---|---|
| **서비스** | **https://bidradar-web-mocha.vercel.app** |
| api | https://bidradar-api.vercel.app (`/api/health`) |
| 발표 자료 | [doc/presentation.pdf](doc/presentation.pdf) (원본: [presentation.md](doc/presentation.md), Marp 슬라이드 15장) |
| **시연 영상** | **https://youtu.be/ssP3JEbc05A** (시연 순서: [doc/demo-script.md](doc/demo-script.md)) |

## 프로젝트 소개
### 해결하려는 문제
- 나라장터에는 하루 수백~수천 건의 공고가 올라온다(용역만 하루 약 600건). 중소기업 입찰 담당자는 매일 직접 검색하고, 공고마다 참가자격·추정가격·마감일을 확인하느라 시간이 많이 든다.
- 기존 알림 서비스는 공고 목록만 주므로 **"우리 회사가 참여할 만한 공고인가?"** 는 여전히 사람이 판단해야 한다.

### 해결 방식
- **수집은 정확하게**: 공공데이터포털 「조달청_나라장터 입찰공고정보서비스」 OpenAPI로 원천 데이터를 가져온다. LLM 웹 검색은 환각·누락 위험이 있어 수집에 쓰지 않는다.
- **AI는 해석에**: 공고 3줄 요약, 회사 프로필 기준 적합도 점수·근거, 자연어 질문을 검색 조건으로 바꾸는 Agent.

### 대상 사용자
공공 입찰에 참여하는 중소 IT·용역·엔지니어링 업체의 영업·입찰 담당자, 공공사업 동향을 살피는 창업자·프리랜서

## 주요 기능
| 화면 | 기능 | 요구사항 |
|---|---|---|
| `/bids`, `/bids/{id}` | 공고 목록·필터(업무 구분·키워드·기관·금액·마감일)·상세, **AI 3줄 요약**("AI 생성" 표시), 첨부파일·나라장터 원문 링크 | FR-03·04 |
| `/chat` | **AI 공고 검색**: "이번 주 마감 설계 용역 찾아줘" → Agent가 검색 조건을 만들어 조회하고 공고번호를 인용해 답변, 이어지는 질문 지원 | FR-07·09 |
| `/recommendations` | **맞춤 추천**: 회사 프로필 기준 적합도 점수(0~100)·근거, 👍/👎는 다음 평가에 반영 | FR-06·08 |
| `/profile` | Google 로그인, 회사 프로필(업종·지역·금액·키워드), 개인정보 동의, **탈퇴(계정·데이터 삭제)** | FR-05, NFR-05 |
| `/settings` | 수집 업무 구분·건수 설정, **지금 수집**(진행 표시, 60초 간격 제한) | FR-02·14 |
| `/feedback` | 만족도·의견 제출 (로그인 없이 가능) | FR-11 |
| (자동) | **매일 09:00 KST 자동 수집 → AI 요약** (Vercel Cron) | FR-01·02 |

## 팀원 및 역할
| 역할 | 담당 업무 | 주요 PR |
|---|---|---|
| **팀장** (PM / Backend / AI) | 기획·일정·Git 관리, 나라장터 수집 클라이언트, FastAPI·서비스 함수, Supabase 저장소, LLM 제공자·AI 요약, **Bid Agent**, **적합도 추천**, 탈퇴 API, 데이터·API 계약서, Vercel 배포, 팀원 PR 리뷰 | #2 #12 #14 #15 #17 #24 #26 #29 |
| **팀원** (Frontend / Data / QA) | Supabase 스키마·RLS 마이그레이션, Next.js 화면 전체(목록·상세·로그인·프로필·설정·피드백·채팅·추천·탈퇴), 한글 글꼴·접근성, 오픈 리다이렉트 방지와 테스트, 사용자 테스트 운영·결과 정리, 팀장 계약서 PR 리뷰 | #10 #13 #16 #19 #20 #22 #27 #32 #33 #35 #38 |

- 협업 방식: 팀장·팀원은 **GitHub 이슈(작업 지시) → 기능 브랜치 → PR → 상대 역할 리뷰 → 병합**으로만 소통했다. 커밋 본문에 `담당: 팀장/팀원`을 남겼다.
- 데이터·API 형식은 [계약서](doc/data-contract.md)로 먼저 합의하고, 계약 변경은 **상대 역할의 리뷰를 받은 뒤** 병합했다 (v1 → v1.1 탈퇴 → v1.2 Agent·추천).
- 리뷰가 실제로 버그를 막은 예: 팀장 검증에서 api의 페이지 범위 오류(#17)를 찾아 수정, 팀원 PR의 **오픈 리다이렉트를 두 차례 변경 요청**해 우회 경로까지 막고 자동 테스트로 고정(#19).

## 기술 스택
| 구분 | 기술 | 선정 근거 (자세한 내용: [PRD 5~6장](doc/prd.md)) |
|---|---|---|
| AI | **Claude API** — Haiku 5.5(요약·추천 평가), Sonnet 5.5(Agent) | 구조화 출력(Pydantic)과 도구 호출 지원. 저비용 모델과 추론 모델을 용도별로 분리. `LLMProvider` 인터페이스로 제공자 교체 가능 |
| Backend | **Python 3.12+, FastAPI** | 공공 API·LLM SDK를 한 언어로, Pydantic으로 API 응답과 LLM 출력을 같은 방식으로 검증 |
| DB / Auth | **Supabase** (PostgreSQL, Auth Google 로그인, RLS) | 서버리스 환경의 영속 저장소, 외래키로 탈퇴 시 데이터 정리 |
| Frontend | **Next.js 16** (App Router, TypeScript, Tailwind, Pretendard) | Vercel과 자연스럽게 배포, 서버 컴포넌트로 목록 렌더링 |
| 배포·자동화 | **Vercel** (함수 리전 `icn1` 서울, GitHub `main` 병합 시 자동 배포, **Vercel Cron**) | 무료 플랜 안에서 web·api·정기 수집을 한 곳에서. 서울 리전으로 공공데이터포털 호출 확인 |

- 계획 대비 변경: **FastMCP(`/mcp`)·n8n·OpenAI 제공자는 범위에서 제외**했다. 필수 기술 요소가 아니고 5일 일정에서 핵심 기능과 사용자 테스트를 우선했다 (PRD 5.2 설계대로 도구 로직은 서비스 함수에 있어 추후 FastMCP로 감싸기 쉽다).

## 시스템 아키텍처
```
[사용자 브라우저]
   │  https://bidradar-web-mocha.vercel.app
   ▼
[web: Next.js (Vercel icn1)] ── 서버 컴포넌트·/api/* 프록시 ──► [api: FastAPI (Vercel icn1)]
   │  Supabase Auth (Google 로그인만)                                │
   │                                                                ├─ 서비스 함수: 수집·검색·상세·설정·프로필·추천
   │                                                                ├─ Bid Agent ─ 도구 호출 ─► 서비스 함수 ─► Claude Sonnet 5.5
   │                                                                ├─ AI 요약 / 적합도 평가 ─► Claude Haiku 5.5
   │                                                                ├─ 수집 ─► 공공데이터포털 나라장터 OpenAPI
   │                                                                └─ Supabase PostgreSQL (service role, RLS)
   │
[Vercel Cron 매일 09:00 KST] ──► GET /api/cron/collect (CRON_SECRET) ─► 수집 → 요약
```
- **web은 DB에 직접 접근하지 않는다.** 데이터는 모두 FastAPI를 거치고, Supabase 클라이언트는 로그인에만 쓴다 ([계약서 1장](doc/data-contract.md)).
- 데이터 모델·API 형식: [doc/data-contract.md](doc/data-contract.md), DB 마이그레이션: [supabase/migrations](supabase/migrations)

## 핵심 AI 활용 (필수 기술 요소 4개)
| 기술 요소 | 구현 | 위치 |
|---|---|---|
| **자동화 워크플로우** | Vercel Cron → 나라장터 수집(중복 제거) → 새 공고 AI 요약 → 저장. "지금 수집"도 같은 흐름 | `api/app/services/bids.py`, `summaries.py`, `api/vercel.json` |
| **AI Agent** | Claude Sonnet 5.5가 질문을 해석해 `search_bids`·`get_bid_detail` 도구를 호출(최대 3단계). "이번 주"·"1억 이하" 같은 표현을 오늘 날짜(요일)와 금액 환산 규칙으로 검색 조건으로 바꿈 | `api/app/services/agent.py`, `api/app/llm/claude.py` |
| **RAG** | Agent가 DB에서 찾은 공고만 근거로 답하고 **공고번호를 인용**, 응답에는 인용한 공고만 카드로 반환 | `agent.py` `_cited` |
| **Long-term Memory** | 회사 프로필과 👍/👎를 저장해 Agent 답변·추천 평가 프롬프트에 반영. 프로필이 바뀌면 다시 평가하고 👍/👎는 유지 | `api/app/services/recommend.py` |

### 프롬프트 설계 요점
- **추측 금지**: 원문(나라장터 필드)·도구 결과에 없는 금액·조건·서류는 만들지 않는다. 값이 없는 항목은 언급하지 않는다.
- **구조화 출력**: 요약(3줄·참가자격·제출서류)과 추천(점수·근거)은 Pydantic 스키마로 검증한다.
- **실측으로 개선**: 요약 문체 혼용·"값 없음" 언급, 첨부파일명을 제출서류로 분류하던 문제를 결과를 보고 두 차례 고쳤다 ([진행 기록](doc/progress.md) D2).
- **실패해도 서비스는 계속**: 요약·추천 평가가 실패하거나 시간을 넘겨도 수집은 성공하고, 남은 공고는 다음 수집·"더 불러오기" 때 처리한다.

## AI 윤리·개인정보
- AI가 만든 요약·추천·답변에는 **"AI 생성" 표시와 모델명**, 나라장터 **원문 링크**를 함께 보여 주고 "참고용"임을 안내한다 (NFR-04).
- 로그인 사용자는 처음 프로필을 저장할 때 **수집 항목·이용 목적·보유 기간에 동의**해야 한다. **탈퇴하면 계정·프로필·추천이 삭제**되고, 피드백은 작성자 정보 없이 익명으로 남는다 (NFR-05).
- 비밀 키는 Vercel Sensitive 환경 변수로만 관리하고, 브라우저에는 공개용(publishable) 키만 둔다. 사용자 경로 입력은 오픈 리다이렉트 검사(`web/lib/safe-path.ts`)를 거친다.

## 사용자 테스트 결과
2026-10-19 21:55~22:17 KST, Production에서 원격 진행. 상세: [doc/user-test.md](doc/user-test.md) 4장
| 항목 | 결과 |
|---|---|
| 참여 | **테스터 5명** (목표 5명 이상 충족) |
| 만족도 | 의견 6건 평균 **4.67 / 5** |
| 안정성 | 테스트 중 api 오류 로그 **0건** |
| 사용 기능 | 프로필 저장 3명, AI 검색 1명, 맞춤 추천 2명(50건 평가), 지금 수집 2명(공고 27 → 47건), 탈퇴 1명 |
| 좋았던 점 | 채팅처럼 입력하는 공고 검색, 맞춤 추천, 즉시 수집, 원문·첨부파일 연결 |

| 발견한 문제 | 반영 |
|---|---|
| 지금 수집에서 새 공고가 0건이면 수집이 안 된 것처럼 보임 (테스터 의견) | ✅ **반영** — 눈에 띄는 안내 상자와 목록 버튼 (#38) |
| 👍/👎를 누른 테스터 0명 — 버튼이 작고 의미가 잘 안 보임 (관찰) | ✅ **반영** — "👍 맞아요 / 👎 아니에요" 버튼, "이 추천이 회사에 맞나요?" 질문과 반영 설명 (#38) |
| 프로필 저장 후 추천 화면으로 돌아오지 않음 (관찰) | ✅ **반영** — 저장 완료 메시지에 "맞춤 추천 보기" 링크 (#38) |
| 가입·탈퇴 안내 메일 요청 | 보류 — Supabase 기본 메일 발송 한도(시간당 2통) |

## 저장소 구조
```
BidRider/
├─ api/          FastAPI 백엔드 (Vercel Python 함수, 리전 icn1, Cron)
│  ├─ app/
│  │  ├─ koneps/      나라장터 OpenAPI 클라이언트
│  │  ├─ llm/         LLMProvider 인터페이스, Claude 구현 (구조화 출력, 도구 호출 루프)
│  │  ├─ services/    수집·검색·요약·Agent·추천·프로필 (도구 로직)
│  │  ├─ repository/  저장소 인터페이스, Supabase·메모리 구현
│  │  └─ routes/      API 라우터
│  └─ tests/     pytest 68건
├─ web/          Next.js 프런트엔드 (node:test 27건)
├─ supabase/     DB 마이그레이션 (스키마·RLS)
└─ doc/          기획서·계약서·진행 기록·사용자 테스트·발표 자료
```

## 문서
| 문서 | 내용 |
|---|---|
| [doc/prd.md](doc/prd.md) | **기획서**: 문제 정의, 대상 사용자, 기술 스택과 선정 근거·불합리한 점, **기능·비기능 요구사항(8·9장)**, **시스템 아키텍처(10장)**, AI 활용 설계, 역할, 일정 |
| [doc/data-contract.md](doc/data-contract.md) | 데이터·API 계약서 (DB 스키마 7개 테이블·RLS, API 요청·응답 형식) |
| [doc/api-research.md](doc/api-research.md) | 나라장터 OpenAPI 조사와 실호출 검증 |
| [doc/progress.md](doc/progress.md) | 일자별 진행 기록과 결정 사항 (팀장·팀원 구역) |
| [doc/user-test.md](doc/user-test.md) | 사용자 테스트 계획·시나리오·결과 |
| [doc/presentation.pdf](doc/presentation.pdf) | 발표 자료 (원본 `presentation.md`, `npx @marp-team/marp-cli doc/presentation.md --pdf`로 생성) |
| [doc/demo-script.md](doc/demo-script.md) | 시연 영상 순서 |

## 실행 방법
### 요구사항
- Python 3.12 이상
- Node.js 20 이상 (web)

### 환경 변수
`.env.example`을 `.env`로 복사한 뒤 값을 채웁니다. `.env`는 커밋하지 않습니다.
- 공공데이터포털 인증키(`DATA_GO_KR_SERVICE_KEY`), Anthropic API 키(`ANTHROPIC_API_KEY`), Supabase URL·키가 필요합니다.
- Supabase 키가 없으면 api는 메모리 저장소로 동작하고, Anthropic 키가 없으면 AI 요약·Agent·추천을 건너뜁니다(Agent·추천 API는 503).

### Backend (Bash)
```bash
python -m venv .venv
source .venv/Scripts/activate   # macOS/Linux: source .venv/bin/activate
pip install -r api/requirements-dev.txt
cd api
uvicorn app.main:app --reload
```
확인: http://127.0.0.1:8000/api/health

### Backend (Windows PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r api\requirements-dev.txt
cd api
uvicorn app.main:app --reload
```

### Frontend (Bash)
api를 먼저 띄운 상태에서 다른 터미널로 실행합니다. `/api/*` 요청은 `API_BASE_URL`(기본 `http://127.0.0.1:8000`)로 프록시됩니다.
```bash
cd web
npm install
cp ../.env.example .env.local   # web 구역(NEXT_PUBLIC_*, API_BASE_URL) 값만 채우고 나머지 줄은 지워도 됩니다
npm run dev
```
확인: http://localhost:3000 (화면에 "API 연결 정상" 표시), http://localhost:3000/bids (공고 목록)

> `API_BASE_URL`은 두 곳에서 쓰입니다. 브라우저의 `/api/*` 프록시(rewrites)는 **빌드 시점**에 값이 고정되고, 서버 컴포넌트의 api 호출(`web/lib/api.ts`)은 **실행 시점**에 읽습니다. Vercel `web` 프로젝트에서 값을 바꾼 뒤에는 **재배포**해야 둘 다 반영됩니다.

### Frontend (Windows PowerShell)
```powershell
cd web
npm install
Copy-Item ..\.env.example .env.local
npm run dev
```

### 테스트
```bash
cd api
pytest                       # 68건 (실제 API 호출 테스트는 RUN_LIVE=1일 때만)
```
```bash
cd web
npm test                     # 27건 (경로 검사)
npm run lint
npm run build
```

### 배포 (Vercel)
- `bidradar-api`(루트 `api`, FastAPI), `bidradar-web`(루트 `web`, Next.js) 두 프로젝트가 GitHub `main`에 연결되어 **병합 시 자동 배포**됩니다.
- 비밀 환경 변수(`DATA_GO_KR_SERVICE_KEY`, `ANTHROPIC_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `CRON_SECRET`)는 Vercel에 Sensitive로 등록합니다. 자세한 기록: [doc/progress.md](doc/progress.md) D3 "1차 배포".
