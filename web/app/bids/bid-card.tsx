import Link from "next/link";
import AiBadge from "@/components/ai-badge";
import ClosingBadge from "@/components/closing-badge";
import { formatDateTime, formatPrice } from "@/lib/format";
import type { Bid } from "@/lib/types";

export default function BidCard({ bid }: { bid: Bid }) {
  return (
    <li>
      <Link
        href={`/bids/${bid.id}`}
        className="flex flex-col gap-3 rounded-xl border border-zinc-200 bg-white p-4 transition hover:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-950 dark:hover:border-zinc-600"
      >
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
            {bid.category}
          </span>
          <ClosingBadge iso={bid.bid_clse_dt} />
          {bid.summary && <AiBadge />}
          <span className="ml-auto text-zinc-500">
            {bid.bid_ntce_no}-{bid.bid_ntce_ord}
          </span>
        </div>
        <h2 className="text-base font-semibold leading-snug">{bid.bid_ntce_nm}</h2>
        {bid.summary && (
          <p className="line-clamp-2 whitespace-pre-line text-sm text-zinc-600 dark:text-zinc-400">
            {bid.summary.summary}
          </p>
        )}
        <dl className="grid grid-cols-1 gap-x-4 gap-y-1 text-sm sm:grid-cols-2">
          <div className="flex gap-2">
            <dt className="shrink-0 text-zinc-500">공고기관</dt>
            <dd className="truncate">{bid.ntce_instt_nm ?? "-"}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="shrink-0 text-zinc-500">추정가격</dt>
            <dd className="font-medium tabular-nums">{formatPrice(bid.presmpt_prce)}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="shrink-0 text-zinc-500">게시</dt>
            <dd className="tabular-nums">{formatDateTime(bid.bid_ntce_dt)}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="shrink-0 text-zinc-500">마감</dt>
            <dd className="tabular-nums">{formatDateTime(bid.bid_clse_dt)}</dd>
          </div>
        </dl>
      </Link>
    </li>
  );
}
