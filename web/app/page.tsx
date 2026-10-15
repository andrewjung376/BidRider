import ApiStatus from "./api-status";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-16 sm:px-8">
      <h1 className="text-3xl font-semibold tracking-tight">BidRadar 입찰레이더</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        나라장터 최신 입찰공고를 수집해 AI가 요약하고, 회사 프로필에 맞는 공고를 추천합니다.
      </p>
      <ApiStatus />
    </main>
  );
}
