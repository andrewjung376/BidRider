"use client";

import Link from "next/link";
import { useState } from "react";

const MAX_MESSAGE = 2000; // api FeedbackIn.message 최대 길이
const RATING_LABELS = ["매우 불만족", "불만족", "보통", "만족", "매우 만족"];

type State = { kind: "idle" } | { kind: "sending" } | { kind: "done"; id: number } | { kind: "error"; message: string };

// FastAPI 오류 응답({"detail": "..."} 또는 422의 [{loc, msg}])을 사람이 읽을 문장으로 바꾼다
function errorMessage(status: number, body: unknown): string {
  if (status === 422) return "입력값을 확인해 주세요. 만족도를 고르고 의견을 2000자 이내로 적어 주세요.";
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  return `제출하지 못했습니다. 잠시 후 다시 시도해 주세요. (${status})`;
}

export default function FeedbackForm({ page }: { page: string | null }) {
  const [rating, setRating] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });

  const trimmed = message.trim();
  const canSubmit = rating !== null && trimmed.length > 0 && trimmed.length <= MAX_MESSAGE && state.kind !== "sending";

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    setState({ kind: "sending" });
    try {
      // 로그인 연동(#7) 전이라 Authorization 헤더 없이 보낸다 (api는 비로그인 제출 허용)
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating, message: trimmed, page }),
      });
      const body = await res.json().catch(() => null);
      if (res.status === 201) {
        setState({ kind: "done", id: body?.id });
      } else {
        setState({ kind: "error", message: errorMessage(res.status, body) });
      }
    } catch {
      setState({ kind: "error", message: "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요." });
    }
  }

  if (state.kind === "done") {
    return (
      <div role="status" className="flex flex-col items-center gap-3 rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-10 text-center dark:border-emerald-800 dark:bg-emerald-950/40">
        <p className="text-lg font-semibold">의견을 보내 주셔서 감사합니다!</p>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">보내 주신 내용은 서비스 개선에 반영하겠습니다.</p>
        <Link href={page ?? "/bids"} className="text-sm underline underline-offset-4">
          {page ? "보던 화면으로 돌아가기" : "입찰공고 보기"}
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-5 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">만족도</legend>
        <div className="grid grid-cols-5 gap-2">
          {RATING_LABELS.map((label, i) => {
            const value = i + 1;
            const selected = rating === value;
            return (
              <button
                key={value}
                type="button"
                onClick={() => setRating(value)}
                aria-pressed={selected}
                aria-label={`${value}점 ${label}`}
                className={`flex h-14 flex-col items-center justify-center rounded-lg border text-lg transition ${
                  selected
                    ? "border-amber-400 bg-amber-50 text-amber-600 dark:border-amber-500 dark:bg-amber-950/50 dark:text-amber-400"
                    : "border-zinc-300 text-zinc-400 hover:border-zinc-400 dark:border-zinc-700 dark:text-zinc-600"
                }`}
              >
                <span aria-hidden>{rating !== null && value <= rating ? "★" : "☆"}</span>
                <span className="text-[10px] leading-none">{value}</span>
              </button>
            );
          })}
        </div>
        <p className="text-xs text-zinc-500">{rating ? RATING_LABELS[rating - 1] : "별을 눌러 골라 주세요."}</p>
      </fieldset>

      <label className="flex flex-col gap-2 text-sm font-medium">
        의견
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={6}
          maxLength={MAX_MESSAGE}
          placeholder="예: 필터에 지역 조건이 있으면 좋겠어요."
          className="rounded-lg border border-zinc-300 bg-white p-3 text-sm font-normal outline-none focus:border-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-400"
        />
        <span className="self-end text-xs font-normal text-zinc-500 tabular-nums">
          {message.length.toLocaleString("ko-KR")} / {MAX_MESSAGE.toLocaleString("ko-KR")}
        </span>
      </label>

      {page && <p className="text-xs text-zinc-500">함께 보낼 화면: {page}</p>}

      {state.kind === "error" && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
          {state.message}
        </p>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="h-11 rounded-lg bg-zinc-900 text-sm font-medium text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
      >
        {state.kind === "sending" ? "보내는 중…" : "의견 보내기"}
      </button>
    </form>
  );
}
