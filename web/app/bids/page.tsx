import type { Metadata } from "next";
import Link from "next/link";
import { fetchBids, PAGE_SIZE, parseBidQuery, toSearchParams } from "@/lib/api";
import type { BidQuery } from "@/lib/types";
import BidCard from "./bid-card";
import BidFilters from "./bid-filters";
import Pagination from "./pagination";

export const metadata: Metadata = { title: "입찰공고" };

function bidsHref(query: BidQuery): string {
  const text = toSearchParams(query).toString();
  return text ? `/bids?${text}` : "/bids";
}

export default async function BidsPage(props: PageProps<"/bids">) {
  const query = parseBidQuery(await props.searchParams);
  const data = await fetchBids(query);
  const totalPages = Math.max(1, Math.ceil(data.total / (data.size || PAGE_SIZE)));
  const hasFilter = Object.keys(query).some((key) => key !== "page");
  // 전체 건수는 있는데 이 페이지가 비었으면 마지막 페이지를 넘은 요청이다
  const outOfRange = data.items.length === 0 && data.total > 0;
  const priceInverted =
    query.min_price !== undefined && query.max_price !== undefined && Number(query.min_price) > Number(query.max_price);
  const firstPageHref = bidsHref({ ...query, page: undefined });

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-bold tracking-tight">입찰공고</h1>
      <BidFilters query={query} />
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        총 <strong className="text-zinc-950 dark:text-zinc-50">{data.total.toLocaleString("ko-KR")}</strong>건
        {data.items.length > 0 && ` · ${data.page}/${totalPages} 페이지`} · 최신 게시순
      </p>

      {priceInverted && (
        <div
          role="alert"
          className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
        >
          <span>최소 금액이 최대 금액보다 큽니다.</span>
          <Link
            href={bidsHref({ ...query, min_price: query.max_price, max_price: query.min_price, page: undefined })}
            className="font-medium underline underline-offset-4"
          >
            최소·최대를 바꿔서 검색
          </Link>
        </div>
      )}

      {outOfRange ? (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-zinc-300 py-16 text-center text-sm text-zinc-600 dark:border-zinc-700 dark:text-zinc-400">
          <p>해당 페이지에 공고가 없습니다. (전체 {totalPages}페이지)</p>
          <Link href={firstPageHref} className="underline underline-offset-4">
            1페이지로
          </Link>
        </div>
      ) : data.items.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-zinc-300 py-16 text-center text-sm text-zinc-600 dark:border-zinc-700 dark:text-zinc-400">
          <p>{hasFilter ? "조건에 맞는 공고가 없습니다." : "아직 수집된 공고가 없습니다."}</p>
          {hasFilter && (
            <Link href="/bids" className="underline underline-offset-4">
              필터 초기화
            </Link>
          )}
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {data.items.map((bid) => (
            <BidCard key={bid.id} bid={bid} />
          ))}
        </ul>
      )}

      {!outOfRange && <Pagination query={query} page={data.page} totalPages={totalPages} />}
      <p className="text-center text-xs text-zinc-500">
        AI 요약은 참고용입니다. 입찰 참여 전 반드시 나라장터 원문을 확인하세요.
      </p>
    </main>
  );
}
