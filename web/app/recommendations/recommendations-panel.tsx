"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import AiBadge from "@/components/ai-badge";
import { useAuth } from "@/components/auth-provider";
import BidCard from "@/components/bid-card";
import { useElapsedSeconds } from "@/components/use-elapsed";
import { apiFetch, ClientApiError } from "@/lib/client-api";
import { getSupabase } from "@/lib/supabase";
import type { FeedbackValue, Recommendation, RecommendationList } from "@/lib/types";

// 계약서 3.4: limit 최대 20, 첫 조회는 평가 때문에 최대 약 30초(요청 제한 60초 이상)
const LIMIT = 20;
const TIMEOUT_MS = 90_000;

// 이벤트·응답 처리 중에만 부르는 현재 시각 (렌더링 중 호출 아님)
const nowMs = () => Date.now();

type Load =
  | { kind: "loading"; startedAt: number }
  | { kind: "ready"; data: RecommendationList }
  | { kind: "no-profile" }
  | { kind: "error"; text: string };

function errorText(e: unknown): string {
  if (e instanceof ClientApiError && e.timedOut) return "평가가 오래 걸려 기다리기를 멈췄습니다. 잠시 후 다시 시도해 주세요.";
  if (e instanceof ClientApiError && e.status === 401) return "로그인이 만료되었습니다. 다시 로그인한 뒤 시도해 주세요.";
  if (e instanceof ClientApiError) return e.message;
  return "추천을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.";
}

function scoreColor(score: number): string {
  if (score >= 70) return "bg-emerald-600 text-white";
  if (score >= 40) return "bg-amber-500 text-white";
  return "bg-zinc-400 text-white dark:bg-zinc-600";
}

function FeedbackButtons({
  value,
  busy,
  onChange,
}: {
  value: FeedbackValue;
  busy: boolean;
  onChange: (next: FeedbackValue) => void;
}) {
  // 사용자 테스트에서 👍/👎를 누른 사람이 0명이라, 글자 라벨과 한 줄 설명을 붙여 크게 보이게 한다
  const base =
    "inline-flex h-10 flex-1 items-center justify-center gap-1.5 rounded-lg border-2 px-4 text-sm font-medium transition disabled:opacity-50 sm:flex-none";
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex gap-2" role="group" aria-label="이 추천이 회사에 맞나요?">
        <button
          type="button"
          disabled={busy}
          aria-pressed={value === 1}
          onClick={() => onChange(value === 1 ? null : 1)}
          className={`${base} ${value === 1 ? "border-emerald-500 bg-emerald-500 text-white" : "border-emerald-300 bg-white text-emerald-700 hover:bg-emerald-50 dark:border-emerald-800 dark:bg-transparent dark:text-emerald-300 dark:hover:bg-emerald-950/50"}`}
        >
          <span aria-hidden>👍</span> 맞아요
        </button>
        <button
          type="button"
          disabled={busy}
          aria-pressed={value === -1}
          onClick={() => onChange(value === -1 ? null : -1)}
          className={`${base} ${value === -1 ? "border-red-500 bg-red-500 text-white" : "border-red-300 bg-white text-red-700 hover:bg-red-50 dark:border-red-800 dark:bg-transparent dark:text-red-300 dark:hover:bg-red-950/50"}`}
        >
          <span aria-hidden>👎</span> 아니에요
        </button>
      </div>
      <p className="text-xs text-zinc-500">
        {value === null ? "누르면 다음 추천에 반영돼요." : "다음 추천에 반영할게요. 같은 버튼을 다시 누르면 취소돼요."}
      </p>
    </div>
  );
}

export default function RecommendationsPanel() {
  const { enabled, loading: authLoading, session, signIn } = useAuth();
  const userId = session?.user.id ?? null;
  const [load, setLoad] = useState<Load | null>(null);
  const [busyBid, setBusyBid] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [moreStartedAt, setMoreStartedAt] = useState<number | null>(null);
  const elapsed = useElapsedSeconds(load?.kind === "loading" ? load.startedAt : moreStartedAt);

  // 같은 요청을 다시 부르면 남은 후보를 더 평가하고, items는 항상 전체 목록이라 통째로 바꾼다 (계약서 3.4)
  // "더 불러오기"는 기존 목록을 그대로 둔 채 버튼에만 진행 표시를 한다
  const fetchRecommendations = useCallback(async (more = false) => {
    if (more) setMoreStartedAt(nowMs());
    else setLoad({ kind: "loading", startedAt: nowMs() });
    setNotice(null);
    try {
      const { data: auth } = (await getSupabase()?.auth.getSession()) ?? { data: { session: null } };
      const { data } = await apiFetch<RecommendationList>(`/api/recommendations?limit=${LIMIT}`, {
        token: auth.session?.access_token,
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      setLoad({ kind: "ready", data });
    } catch (e) {
      if (e instanceof ClientApiError && e.status === 404) setLoad({ kind: "no-profile" });
      else if (more) setNotice(errorText(e));
      else setLoad({ kind: "error", text: errorText(e) });
    } finally {
      if (more) setMoreStartedAt(null);
    }
  }, []);

  // 로그인한 사용자가 정해지면 한 번 불러온다
  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    // 첫 setState를 effect 본문이 아닌 비동기 흐름 안에서 하도록 한 틱 미룬다
    Promise.resolve().then(() => {
      if (!cancelled) fetchRecommendations();
    });
    return () => {
      cancelled = true;
    };
  }, [userId, fetchRecommendations]);

  if (!enabled) {
    return <p className="text-sm text-red-600">로그인 설정(Supabase 환경 변수)이 없어 추천을 쓸 수 없습니다.</p>;
  }
  if (authLoading || (userId && load === null)) {
    return <div className="h-40 animate-pulse rounded-xl bg-zinc-100 dark:bg-zinc-900" aria-busy="true" />;
  }
  if (!session) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-zinc-300 py-12 text-center text-sm dark:border-zinc-700">
        <p>맞춤 추천은 로그인 후 쓸 수 있습니다.</p>
        <button
          type="button"
          onClick={() => signIn("/recommendations")}
          className="h-10 rounded-lg bg-zinc-900 px-4 font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          Google로 로그인
        </button>
      </div>
    );
  }

  async function changeFeedback(item: Recommendation, next: FeedbackValue) {
    if (load?.kind !== "ready" || busyBid !== null) return;
    const bidId = item.bid.id;
    const previous = item.feedback;
    const setFeedback = (value: FeedbackValue) =>
      setLoad((prev) =>
        prev?.kind === "ready"
          ? {
              ...prev,
              data: { ...prev.data, items: prev.data.items.map((r) => (r.bid.id === bidId ? { ...r, feedback: value } : r)) },
            }
          : prev,
      );
    setFeedback(next); // 먼저 화면에 반영하고, 실패하면 되돌린다
    setBusyBid(bidId);
    setNotice(null);
    try {
      await apiFetch("/api/recommendations/" + bidId + "/feedback", {
        method: "POST",
        body: JSON.stringify({ feedback: next }),
        token: session?.access_token,
      });
    } catch (e) {
      setFeedback(previous);
      setNotice(e instanceof ClientApiError ? e.message : "평가를 저장하지 못했습니다.");
    } finally {
      setBusyBid(null);
    }
  }

  if (load?.kind === "no-profile") {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-zinc-300 py-12 text-center text-sm dark:border-zinc-700">
        <p>추천을 받으려면 회사 프로필을 먼저 작성해 주세요.</p>
        <Link
          href="/profile"
          className="inline-flex h-10 items-center rounded-lg bg-zinc-900 px-4 font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          프로필 작성하기
        </Link>
      </div>
    );
  }

  if (load?.kind === "loading") {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-zinc-200 py-12 text-center text-sm text-zinc-600 dark:border-zinc-800 dark:text-zinc-400" aria-busy="true">
        <span className="h-6 w-6 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />
        <p>AI가 프로필에 맞는 공고를 평가하는 중… {elapsed}초</p>
        <p className="text-xs">처음이거나 새 공고가 많으면 최대 30초쯤 걸립니다.</p>
      </div>
    );
  }

  if (load?.kind === "error") {
    return (
      <div className="flex flex-col items-center gap-3 py-8 text-center text-sm">
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-red-700 dark:bg-red-950/50 dark:text-red-300">
          {load.text}
        </p>
        <button
          type="button"
          onClick={() => fetchRecommendations()}
          className="h-10 rounded-lg border border-zinc-300 px-4 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900"
        >
          다시 시도
        </button>
      </div>
    );
  }

  const data = load?.kind === "ready" ? load.data : { items: [], pending: 0 };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-zinc-600 dark:text-zinc-400">
        <span>
          추천 <strong className="text-zinc-950 dark:text-zinc-50">{data.items.length}</strong>건 · 적합도 높은 순
          {data.pending > 0 && ` · 아직 평가하지 않은 공고 ${data.pending}건`}
        </span>
        <Link href="/profile" className="underline underline-offset-4">
          프로필 수정
        </Link>
      </div>

      {notice && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
          {notice}
        </p>
      )}

      {data.items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-300 py-12 text-center text-sm text-zinc-600 dark:border-zinc-700 dark:text-zinc-400">
          {data.pending > 0 ? "아직 평가된 공고가 없습니다. 아래 \"더 불러오기\"를 눌러 주세요." : "추천할 마감 전 공고가 없습니다."}
        </div>
      ) : (
        <ol className="flex flex-col gap-4">
          {data.items.map((item) => (
            <li key={item.bid.id} className="flex flex-col gap-2">
              <div className="flex flex-col gap-2 rounded-xl border border-violet-200 bg-violet-50/50 p-3 dark:border-violet-900 dark:bg-violet-950/30">
                <div className="flex flex-wrap items-center gap-3">
                  <span
                    className={`inline-flex h-10 min-w-14 items-center justify-center rounded-lg px-2 text-lg font-bold tabular-nums ${scoreColor(item.score)}`}
                    aria-label={`적합도 ${item.score}점`}
                  >
                    {item.score}
                  </span>
                  <AiBadge />
                  <span className="text-xs text-zinc-500">{item.model}</span>
                </div>
                <p className="text-sm leading-relaxed">{item.reason}</p>
                <div className="flex flex-col gap-2 border-t border-violet-200 pt-3 sm:flex-row sm:items-start sm:justify-between dark:border-violet-900">
                  <p className="text-sm font-medium">이 추천이 회사에 맞나요?</p>
                  <FeedbackButtons value={item.feedback} busy={busyBid === item.bid.id} onChange={(next) => changeFeedback(item, next)} />
                </div>
              </div>
              <ul>
                <BidCard bid={item.bid} />
              </ul>
            </li>
          ))}
        </ol>
      )}

      {data.pending > 0 && (
        <button
          type="button"
          onClick={() => fetchRecommendations(true)}
          disabled={moreStartedAt !== null}
          aria-busy={moreStartedAt !== null}
          className="inline-flex h-11 items-center gap-2 self-center rounded-lg border border-zinc-300 px-5 text-sm font-medium hover:bg-zinc-100 disabled:opacity-60 dark:border-zinc-700 dark:hover:bg-zinc-900"
        >
          {moreStartedAt !== null && (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />
          )}
          {moreStartedAt !== null ? `평가하는 중… ${elapsed}초` : `더 불러오기 (${data.pending}건 남음)`}
        </button>
      )}

      <p className="text-xs text-zinc-500">
        👍/👎는 다음 평가에 반영되고, 이미 매긴 점수는 바뀌지 않습니다. 같은 버튼을 다시 누르면 취소됩니다. AI 추천은
        참고용이며, 입찰 참여 전 나라장터 원문을 확인하세요.
      </p>
    </div>
  );
}
