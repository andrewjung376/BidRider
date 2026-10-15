# BidRadar (입찰레이더)

> 이 문서는 초안입니다. 기능이 완성되는 대로 결과와 링크를 채웁니다.

## 프로젝트 소개
나라장터 최신 입찰공고를 자동으로 수집해 AI가 요약하고, 회사 프로필에 맞는 공고를 추천하며, 자연어로 검색할 수 있게 하는 서비스입니다.
공고 수집은 공공데이터포털 「조달청_나라장터 입찰공고정보서비스」 OpenAPI로 정확하게 하고, LLM은 해석(요약·자격요건 추출·적합도 판단)과 자연어 검색에 씁니다.

- 기획서: [doc/prd.md](doc/prd.md)
- API 조사: [doc/api-research.md](doc/api-research.md)
- 진행 기록: [doc/progress.md](doc/progress.md)

## 팀원 및 역할
| 역할 | 담당 업무 |
|---|---|
| 팀장 (PM / Backend / AI) | 일정·Git 관리, 공공 API 수집기, 서비스 함수(도구)와 FastMCP 노출, FastAPI, LLMProvider, Bid Agent, 프롬프트, Vercel Cron |
| 팀원 (Frontend / Data / QA) | Next.js UI, Supabase 스키마·Auth·RLS, 피드백 폼, 사용자 테스트 운영, (선택) n8n |

## 기술 스택
- **AI**: Claude API (기본, Haiku 5.5 요약 / Sonnet 5.5 Agent), OpenAI API (선택)
- **Backend**: Python 3.12+, FastAPI, FastMCP (외부 MCP 연동, 선택)
- **DB / Auth**: Supabase (PostgreSQL, 전문검색, Google 로그인, RLS)
- **Frontend**: Next.js (App Router, TypeScript)
- **배포 / 스케줄**: Vercel (함수 리전 `icn1`), Vercel Cron
- **자동화 (선택)**: n8n

선정 근거와 무료 플랜 제약 검토는 [doc/prd.md](doc/prd.md) 5~6장에 있습니다.

## 핵심 AI 활용
| 기술 요소 | 적용 |
|---|---|
| 자동화 워크플로우 | Vercel Cron → 공고 수집 → AI 요약 → Supabase 저장 |
| AI Agent | Bid Agent가 자연어 요청을 해석해 도구(`search_bids` 등)를 호출 |
| Long-term Memory | 사용자별 회사 프로필과 추천 피드백을 저장해 추천에 반영 |
| RAG | 공고 DB 전문검색 결과를 근거로 인용해 답변 |

## 저장소 구조
```
BidRider/
├─ api/          FastAPI 백엔드 (Vercel Python 함수)
│  ├─ app/       애플리케이션 코드
│  └─ tests/     pytest
├─ web/          Next.js 프런트엔드 (예정)
├─ doc/          기획·조사·진행 문서
└─ .env.example  환경 변수 예시
```

## 실행 방법
### 요구사항
- Python 3.12 이상
- Node.js 20 이상 (web, 예정)

### 환경 변수
`.env.example`을 `.env`로 복사한 뒤 값을 채웁니다. `.env`는 커밋하지 않습니다.

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

### 테스트
```bash
cd api
pytest
```

## AI 윤리
- AI가 생성한 요약·추천에는 "AI 생성" 표시와 원문 링크를 함께 보여 줍니다.
- 로그인 시 수집 항목(이메일, 회사 프로필)과 이용 목적에 대한 동의를 받고, 탈퇴 시 데이터를 삭제합니다.

## 사용자 테스트 결과
(10/20 테스트 후 작성 예정)

## 링크
- 배포 URL: (예정)
- 발표 자료: (예정)
- 시연 영상: (예정)
