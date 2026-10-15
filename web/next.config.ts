import type { NextConfig } from "next";

// /api/* 요청을 FastAPI(api 프로젝트)로 프록시한다. 두 Vercel 프로젝트 간 CORS를 피하기 위함 (PRD 5.3)
// 로컬: http://127.0.0.1:8000, 배포: Vercel web 프로젝트 환경 변수에 api 프로젝트 URL 지정
const apiBaseUrl = (process.env.API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiBaseUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
