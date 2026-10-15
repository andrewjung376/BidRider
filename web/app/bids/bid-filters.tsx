import Link from "next/link";
import { CATEGORIES, type BidQuery } from "@/lib/types";

const inputClass =
  "h-10 w-full rounded-lg border border-zinc-300 bg-white px-3 text-sm outline-none focus:border-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-400";
const labelClass = "flex flex-col gap-1 text-xs font-medium text-zinc-600 dark:text-zinc-400";

// GET 폼이라 JavaScript 없이도 동작한다. 제출하면 page가 빠져 1페이지부터 다시 조회한다.
export default function BidFilters({ query }: { query: BidQuery }) {
  return (
    <form
      action="/bids"
      method="get"
      className="grid grid-cols-1 gap-3 rounded-xl border border-zinc-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4 dark:border-zinc-800 dark:bg-zinc-950"
    >
      <label className={labelClass}>
        업무 구분
        <select name="category" defaultValue={query.category ?? ""} className={inputClass}>
          <option value="">전체</option>
          {CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
      </label>
      <label className={labelClass}>
        키워드 (공고명)
        <input name="q" defaultValue={query.q} placeholder="예: GIS" className={inputClass} />
      </label>
      <label className={labelClass}>
        기관 (공고·수요기관)
        <input name="institution" defaultValue={query.institution} placeholder="예: 광주" className={inputClass} />
      </label>
      <div className={labelClass}>
        추정가격 (원)
        <div className="flex items-center gap-2">
          <input
            name="min_price"
            type="number"
            min={0}
            inputMode="numeric"
            defaultValue={query.min_price}
            placeholder="최소"
            aria-label="추정가격 최소"
            className={inputClass}
          />
          <span aria-hidden>~</span>
          <input
            name="max_price"
            type="number"
            min={0}
            inputMode="numeric"
            defaultValue={query.max_price}
            placeholder="최대"
            aria-label="추정가격 최대"
            className={inputClass}
          />
        </div>
      </div>
      <div className={`${labelClass} sm:col-span-2`}>
        입찰마감일
        <div className="flex items-center gap-2">
          <input
            name="closing_from"
            type="date"
            defaultValue={query.closing_from}
            aria-label="입찰마감일 시작"
            className={inputClass}
          />
          <span aria-hidden>~</span>
          <input
            name="closing_to"
            type="date"
            defaultValue={query.closing_to}
            aria-label="입찰마감일 끝"
            className={inputClass}
          />
        </div>
      </div>
      <div className="flex items-end gap-2 sm:col-span-2">
        <button
          type="submit"
          className="h-10 flex-1 rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          검색
        </button>
        <Link
          href="/bids"
          className="inline-flex h-10 items-center rounded-lg border border-zinc-300 px-4 text-sm hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900"
        >
          초기화
        </Link>
      </div>
    </form>
  );
}
