import Link from "next/link";
import AuthButton from "./auth-button";
import FeedbackLink from "./feedback-link";

const navLink = "text-sm text-zinc-600 hover:text-zinc-950 dark:text-zinc-400 dark:hover:text-zinc-50";

export default function SiteHeader() {
  return (
    <header className="border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <nav className="mx-auto flex h-14 w-full max-w-5xl items-center gap-4 px-4 sm:gap-6 sm:px-6">
        <Link href="/" className="text-lg font-bold tracking-tight">
          BidRadar
        </Link>
        <Link href="/bids" className={navLink}>
          입찰공고
        </Link>
        <FeedbackLink className={`${navLink} ml-auto`}>의견 보내기</FeedbackLink>
        <AuthButton />
      </nav>
    </header>
  );
}
