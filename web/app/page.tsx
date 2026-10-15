import Link from "next/link";
import ApiStatus from "./api-status";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-4 py-16 sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight">BidRadar 입찰레이더</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        나라장터 최신 입찰공고를 수집해 AI가 요약하고, 회사 프로필에 맞는 공고를 추천합니다.
      </p>
      <div>
        <Link
          href="/bids"
          className="inline-flex h-11 items-center rounded-lg bg-zinc-900 px-5 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          입찰공고 보기
        </Link>
      </div>
      <ApiStatus />
    </main>
  );
}
