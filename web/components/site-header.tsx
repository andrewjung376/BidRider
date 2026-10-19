import Link from "next/link";
import AuthButton from "./auth-button";
import FeedbackLink from "./feedback-link";

const navLink = "whitespace-nowrap text-sm text-zinc-600 hover:text-zinc-950 dark:text-zinc-400 dark:hover:text-zinc-50";

export default function SiteHeader() {
  return (
    <header className="border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <nav className="mx-auto flex h-14 w-full max-w-5xl items-center gap-3 px-4 sm:gap-6 sm:px-6">
        <Link href="/" className="text-lg font-bold tracking-tight">
          BidRadar
        </Link>
        {/* 휴대폰 폭에서 메뉴가 넘치면 이 영역만 가로로 밀어서 본다 */}
        <div className="flex min-w-0 flex-1 items-center gap-3 overflow-x-auto [scrollbar-width:none] sm:gap-6">
          <Link href="/bids" className={navLink}>
            입찰공고
          </Link>
          <Link href="/chat" className={navLink}>
            AI 검색
          </Link>
          <Link href="/recommendations" className={navLink}>
            추천
          </Link>
          <Link href="/settings" className={navLink}>
            수집 설정
          </Link>
        </div>
        <div className="flex shrink-0 items-center gap-3 sm:gap-6">
          {/* 휴대폰 폭에서는 하단(footer)의 의견 보내기 링크를 쓴다 */}
          <FeedbackLink className={`${navLink} hidden sm:inline`}>의견 보내기</FeedbackLink>
          <AuthButton />
        </div>
      </nav>
    </header>
  );
}
