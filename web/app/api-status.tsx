"use client";

import { useEffect, useState } from "react";

type Status = "checking" | "ok" | "error";

// web → (rewrites) → api 연결 확인용. GET /api/health 응답을 표시한다
export default function ApiStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    fetch("/api/health")
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((body: { status?: string }) => setStatus(body.status === "ok" ? "ok" : "error"))
      .catch(() => setStatus("error"));
  }, []);

  const label = {
    checking: "API 연결 확인 중…",
    ok: "API 연결 정상",
    error: "API 연결 실패",
  }[status];

  const color = {
    checking: "bg-zinc-400",
    ok: "bg-emerald-500",
    error: "bg-red-500",
  }[status];

  return (
    <div className="flex flex-col gap-1 text-sm text-zinc-600 dark:text-zinc-400">
      <p className="inline-flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${color}`} aria-hidden />
        {label}
      </p>
      {status === "error" && (
        <p className="text-xs">
          api 서버(<code>API_BASE_URL</code>, 기본 http://127.0.0.1:8000)가 실행 중인지 확인하세요.
        </p>
      )}
    </div>
  );
}
