import type { Metadata } from "next";
import { parseSafePath } from "@/lib/safe-path";
import FeedbackForm from "./feedback-form";

export const metadata: Metadata = { title: "의견 보내기" };

export default async function FeedbackPage(props: PageProps<"/feedback">) {
  // ?from= 은 이 서비스 안의 경로일 때만 쓴다 (화면 표시, page 저장, 돌아가기 링크)
  const from = parseSafePath((await props.searchParams).from);

  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col gap-4 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-bold tracking-tight">의견 보내기</h1>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        BidRadar를 써 보신 느낌을 알려 주세요. 불편했던 점, 있었으면 하는 기능 모두 좋습니다. 로그인하지 않아도
        보낼 수 있습니다.
      </p>
      <FeedbackForm page={from} />
    </main>
  );
}
