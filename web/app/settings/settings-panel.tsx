"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { apiFetch, ClientApiError } from "@/lib/client-api";
import { formatDateTime } from "@/lib/format";
import { CATEGORIES, type Category, type CollectResult, type CollectSettings } from "@/lib/types";

// 공공데이터포털 응답이 호출당 수 초~십수 초, 업무 구분 수만큼 더 걸린다 (팀장 #8 코멘트: 최소 60초)
const COLLECT_TIMEOUT_MS = 90_000;
// api의 수동 수집 간격 제한(MANUAL_COLLECT_INTERVAL_SECONDS)과 같게 둔다. 실제 제한은 api의 429가 기준
const COLLECT_INTERVAL_SECONDS = 60;

type Notice = { kind: "success" | "error"; text: string } | null;
type CollectState =
  | { kind: "idle" }
  | { kind: "running"; startedAt: number }
  | { kind: "done"; result: CollectResult }
  | { kind: "error"; text: string };

const primaryButton =
  "h-11 rounded-lg bg-zinc-900 px-5 text-sm font-medium text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300";

export default function SettingsPanel({ initial }: { initial: CollectSettings }) {
  const { enabled, loading: authLoading, session, signIn } = useAuth();
  const [saved, setSaved] = useState(initial);
  const [categories, setCategories] = useState<Category[]>(initial.categories);
  const [numRows, setNumRows] = useState(String(initial.num_rows));
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [collect, setCollect] = useState<CollectState>({ kind: "idle" });
  const [cooldownUntil, setCooldownUntil] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());

  // 수집 중 경과 시간과 재수집 대기 시간을 1초마다 갱신
  const ticking = collect.kind === "running" || (cooldownUntil !== null && cooldownUntil > now);
  useEffect(() => {
    if (!ticking) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [ticking]);

  const loggedIn = Boolean(session);
  const rows = Number(numRows);
  const rowsValid = Number.isInteger(rows) && rows >= 1 && rows <= 100;
  const formValid = categories.length > 0 && rowsValid;
  const dirty =
    rows !== saved.num_rows ||
    categories.length !== saved.categories.length ||
    categories.some((c) => !saved.categories.includes(c));
  const cooldownLeft = cooldownUntil ? Math.max(0, Math.ceil((cooldownUntil - now) / 1000)) : 0;
  const running = collect.kind === "running";
  const elapsed = running ? Math.floor((now - collect.startedAt) / 1000) : 0;

  function toggle(category: Category) {
    // 화면 순서(CATEGORIES)대로 유지
    setCategories((prev) =>
      prev.includes(category) ? prev.filter((c) => c !== category) : CATEGORIES.filter((c) => c === category || prev.includes(c)),
    );
    setNotice(null);
  }

  async function onSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!formValid || !loggedIn || saving) return;
    setSaving(true);
    setNotice(null);
    try {
      const { data } = await apiFetch<CollectSettings>("/api/settings", {
        method: "PUT",
        body: JSON.stringify({ categories, num_rows: rows }),
        token: session?.access_token,
      });
      setSaved(data);
      setCategories(data.categories);
      setNumRows(String(data.num_rows));
      setNotice({ kind: "success", text: "수집 설정을 저장했습니다. 다음 정기 수집부터 적용됩니다." });
    } catch (error) {
      setNotice({ kind: "error", text: error instanceof ClientApiError ? error.message : "저장하지 못했습니다." });
    } finally {
      setSaving(false);
    }
  }

  async function onCollect() {
    if (!formValid || !loggedIn || running || cooldownLeft > 0) return;
    const startedAt = Date.now();
    setNow(startedAt);
    setCollect({ kind: "running", startedAt });
    try {
      // 화면에서 고른 업무 구분·건수로 수집한다 (저장하지 않은 변경도 이번 수집에만 적용)
      const { data } = await apiFetch<CollectResult>("/api/collect", {
        method: "POST",
        body: JSON.stringify({ categories, num_rows: rows }),
        token: session?.access_token,
        signal: AbortSignal.timeout(COLLECT_TIMEOUT_MS),
      });
      setCollect({ kind: "done", result: data });
      setCooldownUntil(Date.now() + COLLECT_INTERVAL_SECONDS * 1000);
    } catch (error) {
      let text = "수집하지 못했습니다. 잠시 후 다시 시도해 주세요.";
      if (error instanceof ClientApiError) {
        if (error.status === 429) {
          const wait = error.retryAfter ?? COLLECT_INTERVAL_SECONDS;
          setCooldownUntil(Date.now() + wait * 1000);
          text = `최근에 수집했습니다. ${wait}초 후에 다시 수집할 수 있습니다.`;
        } else if (error.timedOut) {
          text =
            "응답이 늦어 화면에서 기다리기를 멈췄습니다. 서버에서는 수집이 계속될 수 있으니 잠시 후 입찰공고 목록을 확인해 주세요.";
        } else {
          text = error.message; // 502: 공공데이터포털 실패 사유, 401: 로그인 필요 등
        }
      }
      setCollect({ kind: "error", text });
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {enabled && !authLoading && !loggedIn && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900 dark:border-sky-900 dark:bg-sky-950/40 dark:text-sky-200">
          <span>설정 저장과 &quot;지금 수집&quot;은 로그인해야 쓸 수 있습니다.</span>
          <button type="button" onClick={() => signIn("/settings")} className="font-medium underline underline-offset-4">
            Google로 로그인
          </button>
        </div>
      )}

      <form onSubmit={onSave} className="flex flex-col gap-5 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 text-sm font-medium">업무 구분 (하나 이상)</legend>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {CATEGORIES.map((category) => {
              const checked = categories.includes(category);
              return (
                <label
                  key={category}
                  className={`flex h-11 cursor-pointer items-center justify-center gap-2 rounded-lg border text-sm transition ${
                    checked
                      ? "border-zinc-900 bg-zinc-900 font-medium text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900"
                      : "border-zinc-300 hover:border-zinc-500 dark:border-zinc-700"
                  }`}
                >
                  <input type="checkbox" checked={checked} onChange={() => toggle(category)} className="sr-only" />
                  {category}
                </label>
              );
            })}
          </div>
          {categories.length === 0 && (
            <p className="text-xs text-red-600 dark:text-red-400">업무 구분을 하나 이상 선택해 주세요.</p>
          )}
        </fieldset>

        <label className="flex flex-col gap-2 text-sm font-medium">
          업무 구분당 수집 건수 (1~100)
          <input
            type="number"
            min={1}
            max={100}
            inputMode="numeric"
            value={numRows}
            onChange={(e) => {
              setNumRows(e.target.value);
              setNotice(null);
            }}
            className="h-10 w-32 rounded-lg border border-zinc-300 bg-white px-3 text-sm font-normal outline-none focus:border-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-400"
          />
          {!rowsValid && <span className="text-xs font-normal text-red-600 dark:text-red-400">1~100 사이 정수로 입력해 주세요.</span>}
        </label>

        <p className="text-xs text-zinc-500">
          저장된 설정: {saved.categories.join(", ")} · {saved.num_rows}건 · 마지막 수정 {formatDateTime(saved.updated_at)}
        </p>

        {notice && (
          <p
            role={notice.kind === "error" ? "alert" : "status"}
            className={`rounded-lg px-3 py-2 text-sm ${
              notice.kind === "error"
                ? "bg-red-50 text-red-700 dark:bg-red-950/50 dark:text-red-300"
                : "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200"
            }`}
          >
            {notice.text}
          </p>
        )}

        <button type="submit" disabled={!formValid || !loggedIn || saving || !dirty} className={`${primaryButton} self-start`}>
          {saving ? "저장 중…" : dirty ? "설정 저장" : "변경 사항 없음"}
        </button>
      </form>

      <section className="flex flex-col gap-3 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="font-semibold">지금 수집</h2>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          위에서 고른 업무 구분({categories.join(", ") || "선택 없음"})의 최신 공고를 업무 구분당 {rowsValid ? rows : "-"}건씩
          가져옵니다. 공공데이터포털 응답에 수십 초 걸릴 수 있습니다.
        </p>
        <button
          type="button"
          onClick={onCollect}
          disabled={!formValid || !loggedIn || running || cooldownLeft > 0}
          aria-busy={running}
          className={`${primaryButton} inline-flex items-center justify-center gap-2 self-start`}
        >
          {running && <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />}
          {running ? `수집 중… ${elapsed}초` : cooldownLeft > 0 ? `${cooldownLeft}초 후 다시 수집 가능` : "지금 수집"}
        </button>

        <div aria-live="polite">
          {running && (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              나라장터 공고를 가져오고 AI 요약을 만드는 중입니다. 이 화면을 닫지 말고 기다려 주세요.
            </p>
          )}
          {collect.kind === "done" && (
            <div className="flex flex-col gap-2 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">
              <p className="font-medium">수집을 마쳤습니다. ({collect.result.categories.join(", ")})</p>
              <dl className="flex gap-6">
                <div>
                  <dt className="text-xs opacity-80">받은 공고</dt>
                  <dd className="text-lg font-semibold tabular-nums">{collect.result.fetched_count}건</dd>
                </div>
                <div>
                  <dt className="text-xs opacity-80">새로 저장</dt>
                  <dd className="text-lg font-semibold tabular-nums">{collect.result.inserted_count}건</dd>
                </div>
              </dl>
              {collect.result.inserted_count === 0 && (
                <p className="text-xs opacity-80">이미 저장된 공고와 같아 새로 추가된 공고가 없습니다.</p>
              )}
              <Link href="/bids" className="self-start underline underline-offset-4">
                입찰공고 목록에서 보기
              </Link>
            </div>
          )}
          {collect.kind === "error" && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
              {collect.text}
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
