# BidRadar web (Next.js)

BidRadar 프런트엔드입니다. 실행 방법과 환경 변수는 저장소 루트 [README.md](../README.md)를 참고하세요.

- App Router, TypeScript, Tailwind CSS
- `/api/*` 요청은 `next.config.ts`의 rewrites로 FastAPI(`API_BASE_URL`)에 프록시
- 데이터·API 형식: [doc/data-contract.md](../doc/data-contract.md)
