import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import AiBadge from "@/components/ai-badge";
import ClosingBadge from "@/components/closing-badge";
import { fetchBid } from "@/lib/api";
import { formatDateTime, formatPrice } from "@/lib/format";

export async function generateMetadata(props: PageProps<"/bids/[id]">): Promise<Metadata> {
  const bid = await fetchBid((await props.params).id);
  return { title: bid?.bid_ntce_nm ?? "공고를 찾을 수 없습니다" };
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 border-b border-zinc-100 py-2 sm:flex-row sm:gap-4 dark:border-zinc-900">
      <dt className="shrink-0 text-sm text-zinc-500 sm:w-28">{label}</dt>
      <dd className="text-sm break-all">{children}</dd>
    </div>
  );
}

const linkClass = "text-sky-700 underline underline-offset-4 hover:text-sky-900 dark:text-sky-400 dark:hover:text-sky-300";

export default async function BidDetailPage(props: PageProps<"/bids/[id]">) {
  const bid = await fetchBid((await props.params).id);
  if (!bid) notFound();

  const originalLink = bid.bid_ntce_dtl_url ? (
    <a href={bid.bid_ntce_dtl_url} target="_blank" rel="noopener noreferrer" className={linkClass}>
      나라장터 원문 보기
    </a>
  ) : null;

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6">
      <Link href="/bids" className="text-sm text-zinc-600 hover:text-zinc-950 dark:text-zinc-400 dark:hover:text-zinc-50">
        ← 목록으로
      </Link>

      <header className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
            {bid.category}
          </span>
          <ClosingBadge iso={bid.bid_clse_dt} />
        </div>
        <h1 className="text-xl font-bold leading-snug sm:text-2xl">{bid.bid_ntce_nm}</h1>
        {bid.bid_ntce_dtl_url && (
          <div>
            <a
              href={bid.bid_ntce_dtl_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-10 items-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
            >
              나라장터 원문 보기 ↗
            </a>
          </div>
        )}
      </header>

      <section className="flex flex-col gap-3 rounded-xl border border-violet-200 bg-violet-50/50 p-4 dark:border-violet-900 dark:bg-violet-950/30">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-semibold">AI 요약</h2>
          {bid.summary && <AiBadge />}
        </div>
        {bid.summary ? (
          <>
            <p className="whitespace-pre-line text-sm leading-relaxed">{bid.summary.summary}</p>
            <dl className="flex flex-col gap-2 text-sm">
              <div>
                <dt className="font-medium">참가자격</dt>
                <dd className="whitespace-pre-line text-zinc-700 dark:text-zinc-300">
                  {bid.summary.qualifications ?? "공고 정보에 없음 — 원문을 확인하세요."}
                </dd>
              </div>
              <div>
                <dt className="font-medium">제출서류</dt>
                <dd className="text-zinc-700 dark:text-zinc-300">
                  {bid.summary.required_documents.length > 0 ? (
                    <ul className="list-inside list-disc">
                      {bid.summary.required_documents.map((doc) => (
                        <li key={doc}>{doc}</li>
                      ))}
                    </ul>
                  ) : (
                    "공고문(첨부파일)에서 확인하세요."
                  )}
                </dd>
              </div>
            </dl>
            <p className="text-xs text-zinc-500">
              {bid.summary.model}이 나라장터 공고 정보로 생성한 참고용 요약입니다. 정확한 내용은 {originalLink ?? "나라장터 원문"}
              에서 확인하세요.
            </p>
          </>
        ) : (
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            아직 요약이 없습니다. 다음 수집 때 생성됩니다.
          </p>
        )}
      </section>

      <section>
        <h2 className="mb-1 font-semibold">공고 정보</h2>
        <dl>
          <Field label="공고번호">
            {bid.bid_ntce_no}-{bid.bid_ntce_ord}
          </Field>
          <Field label="공고기관">{bid.ntce_instt_nm ?? "-"}</Field>
          <Field label="수요기관">{bid.dminstt_nm ?? "-"}</Field>
          <Field label="추정가격">
            <span className="font-medium tabular-nums">{formatPrice(bid.presmpt_prce)}</span>
          </Field>
          <Field label="게시일시">{formatDateTime(bid.bid_ntce_dt)}</Field>
          <Field label="입찰마감">{formatDateTime(bid.bid_clse_dt)}</Field>
          <Field label="개찰일시">{formatDateTime(bid.openg_dt)}</Field>
          <Field label="원문">{originalLink ?? "-"}</Field>
        </dl>
      </section>

      <section>
        <h2 className="mb-2 font-semibold">첨부파일</h2>
        {bid.attachments.length > 0 ? (
          <ul className="flex flex-col gap-1 text-sm">
            {bid.attachments.map((file) => (
              <li key={file.url}>
                <a href={file.url} target="_blank" rel="noopener noreferrer" className={`${linkClass} break-all`}>
                  {file.name}
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-zinc-600 dark:text-zinc-400">첨부파일이 없습니다.</p>
        )}
      </section>
    </main>
  );
}
