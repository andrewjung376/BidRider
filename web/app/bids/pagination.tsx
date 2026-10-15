import Link from "next/link";
import { toSearchParams } from "@/lib/api";
import type { BidQuery } from "@/lib/types";

const WINDOW = 2; // 현재 페이지 앞뒤로 보여 줄 번호 수

function pageHref(query: BidQuery, page: number): string {
  const params = toSearchParams({ ...query, page: page > 1 ? String(page) : undefined });
  const text = params.toString();
  return text ? `/bids?${text}` : "/bids";
}

export default function Pagination({ query, page, totalPages }: { query: BidQuery; page: number; totalPages: number }) {
  if (totalPages <= 1) return null;
  const start = Math.max(1, page - WINDOW);
  const end = Math.min(totalPages, page + WINDOW);
  const pages = Array.from({ length: end - start + 1 }, (_, i) => start + i);

  const base = "inline-flex h-9 min-w-9 items-center justify-center rounded-lg px-3 text-sm";
  const idle = `${base} border border-zinc-300 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900`;
  const disabled = `${base} border border-zinc-200 text-zinc-400 dark:border-zinc-800 dark:text-zinc-600`;

  return (
    <nav aria-label="페이지 이동" className="flex flex-wrap items-center justify-center gap-1">
      {page > 1 ? (
        <Link href={pageHref(query, page - 1)} className={idle}>
          이전
        </Link>
      ) : (
        <span className={disabled}>이전</span>
      )}
      {pages.map((p) =>
        p === page ? (
          <span
            key={p}
            aria-current="page"
            className={`${base} bg-zinc-900 font-medium text-white dark:bg-zinc-100 dark:text-zinc-900`}
          >
            {p}
          </span>
        ) : (
          <Link key={p} href={pageHref(query, p)} className={idle}>
            {p}
          </Link>
        ),
      )}
      {page < totalPages ? (
        <Link href={pageHref(query, page + 1)} className={idle}>
          다음
        </Link>
      ) : (
        <span className={disabled}>다음</span>
      )}
    </nav>
  );
}
