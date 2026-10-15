import type { Metadata } from "next";
import FeedbackForm from "./feedback-form";

export const metadata: Metadata = { title: "의견 보내기" };

const MAX_PAGE_LENGTH = 200; // api FeedbackIn.page 최대 길이

/** ?from= 값이 이 서비스 안의 경로일 때만 쓴다 */
function parseFrom(value: string | string[] | undefined): string | null {
  const text = Array.isArray(value) ? value[0] : value;
  if (!text || !text.startsWith("/") || text.startsWith("//")) return null;
  return text.slice(0, MAX_PAGE_LENGTH);
}

export default async function FeedbackPage(props: PageProps<"/feedback">) {
  const from = parseFrom((await props.searchParams).from);

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
