"use client";

import { useEffect } from "react";

// 공고 목록·상세에서 api 호출이 실패했을 때
export default function BidsError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col items-center gap-3 px-4 py-16 text-center sm:px-6">
      <h1 className="text-lg font-semibold">공고를 불러오지 못했습니다.</h1>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        api 서버(<code>API_BASE_URL</code>, 기본 http://127.0.0.1:8000)가 실행 중인지 확인한 뒤 다시 시도하세요.
      </p>
      <button
        type="button"
        onClick={() => retry()}
        className="h-10 rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
      >
        다시 시도
      </button>
    </main>
  );
}
