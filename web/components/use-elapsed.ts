"use client";

import { useEffect, useState } from "react";

/** startedAt(ms)부터 지난 초. null이면 0이고 타이머를 멈춘다 (오래 걸리는 LLM 요청의 경과 시간 표시용) */
export function useElapsedSeconds(startedAt: number | null): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (startedAt === null) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  return startedAt === null ? 0 : Math.max(0, Math.floor((now - startedAt) / 1000));
}
