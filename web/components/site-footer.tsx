import FeedbackLink from "./feedback-link";

export default function SiteFooter() {
  return (
    <footer className="border-t border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-1 px-4 py-6 text-xs text-zinc-500 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p>공고 출처: 조달청 나라장터(공공데이터포털). AI 요약·추천은 참고용입니다.</p>
        <FeedbackLink className="underline underline-offset-4 hover:text-zinc-950 dark:hover:text-zinc-50">
          사용해 보신 의견을 보내 주세요
        </FeedbackLink>
      </div>
    </footer>
  );
}
