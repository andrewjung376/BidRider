import Link from "next/link";

export default function BidNotFound() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center gap-3 px-4 py-16 text-center sm:px-6">
      <h1 className="text-lg font-semibold">공고를 찾을 수 없습니다.</h1>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">삭제되었거나 잘못된 주소입니다.</p>
      <Link href="/bids" className="text-sm underline underline-offset-4">
        목록으로 돌아가기
      </Link>
    </main>
  );
}
