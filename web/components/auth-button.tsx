"use client";

import Link from "next/link";
import { useAuth } from "./auth-provider";

const buttonClass =
  "inline-flex h-8 items-center rounded-lg border border-zinc-300 px-3 text-sm hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900";

// 상단 메뉴의 로그인 상태 표시
export default function AuthButton() {
  const { enabled, loading, session, signIn, signOut } = useAuth();
  if (!enabled) return null;
  if (loading) return <span className="h-8 w-16 animate-pulse rounded-lg bg-zinc-100 dark:bg-zinc-900" aria-hidden />;

  if (!session) {
    return (
      <button type="button" onClick={() => signIn()} className={buttonClass}>
        로그인
      </button>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <Link
        href="/profile"
        title={session.user.email}
        className="max-w-40 truncate text-sm text-zinc-600 hover:text-zinc-950 dark:text-zinc-400 dark:hover:text-zinc-50"
      >
        <span className="sm:hidden">프로필</span>
        <span className="hidden sm:inline">{session.user.email ?? "프로필"}</span>
      </Link>
      <button type="button" onClick={() => signOut()} className={buttonClass}>
        로그아웃
      </button>
    </div>
  );
}
