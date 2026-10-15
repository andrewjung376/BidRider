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

### 확인 필요
- Vercel Python 런타임이 `api/main.py`의 `app`을 진입점으로 인식하는지 (첫 배포 시 확인)
- Vercel Python 버전(3.12) vs 로컬 3.13 차이로 인한 문제 여부
- 공공데이터포털 참고문서(docx)로 오퍼레이션·파라미터 검증

### 다음 할 일
- 팀장: 나라장터 수집 클라이언트 PoC (인증키 발급 후 호출 확인), 서비스 함수 정의, LLMProvider 인터페이스
- 팀원: Supabase 프로젝트(서울)·스키마·RLS·Google 로그인 설정, Next.js 스캐폴드, Vercel 프로젝트 2개 연결
- 공통: 테스터 5명 이상 모집
