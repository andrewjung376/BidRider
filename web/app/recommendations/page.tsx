import type { Metadata } from "next";
import RecommendationsPanel from "./recommendations-panel";

export const metadata: Metadata = { title: "맞춤 추천" };

export default function RecommendationsPage() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-bold tracking-tight">맞춤 추천</h1>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        회사 프로필을 기준으로 아직 마감되지 않은 최신 공고의 적합도(0~100점)를 AI가 평가합니다. 👍/👎를 남기면 다음
        평가에 반영됩니다.
      </p>
      <RecommendationsPanel />
    </main>
  );
}
