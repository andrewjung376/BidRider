import type { Metadata } from "next";
import FeedbackForm from "./feedback-form";

export const metadata: Metadata = { title: "의견 보내기" };

const MAX_PAGE_LENGTH = 200; // api FeedbackIn.page 최대 길이
const SAME_ORIGIN = "http://local";
// 역슬래시는 브라우저가 "/"로 바꿔 읽고(/\evil.com → //evil.com), 탭·줄바꿈은 URL 해석 때 지워진다
const UNSAFE_CHARS = /[\\\u0000-\u001f\u007f]/;

/**
 * ?from= 값이 이 서비스 안의 경로일 때만 쓴다 (오픈 리다이렉트 방지).
 * 이 값은 화면 표시, 피드백의 page 저장, "보던 화면으로 돌아가기" 링크에 그대로 쓰인다.
 */
function parseFrom(value: string | string[] | undefined): string | null {
  const text = Array.isArray(value) ? value[0] : value;
  if (!text || !text.startsWith("/") || UNSAFE_CHARS.test(text)) return null;
  let url: URL;
  try {
    url = new URL(text, SAME_ORIGIN);
  } catch {
    return null;
  }
  if (url.origin !== SAME_ORIGIN) return null;
  return (url.pathname + url.search).slice(0, MAX_PAGE_LENGTH);
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
