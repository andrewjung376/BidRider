"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { apiFetch, ClientApiError } from "@/lib/client-api";
import { getSupabase } from "@/lib/supabase";

const CONFIRM_WORD = "탈퇴";

// 탈퇴(계정 삭제, NFR-05): DELETE /api/me → 204 → signOut → 홈 (계약서 v1.1)
export default function DeleteAccount() {
  const router = useRouter();
  const { loading, session } = useAuth();
  const [open, setOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 비로그인 상태에서는 보이지 않는다
  if (loading || !session) return null;

  const confirmed = confirmText.trim() === CONFIRM_WORD;

  async function onDelete() {
    if (!confirmed || deleting) return;
    setDeleting(true);
    setError(null);
    try {
      await apiFetch<null>("/api/me", { method: "DELETE", token: session?.access_token });
      // 계정이 지워져 서버가 401·403·404를 돌려줘도 supabase-js는 브라우저 세션을 지운다
      await getSupabase()?.auth.signOut();
      router.replace("/?account=deleted");
    } catch (e) {
      setError(
        e instanceof ClientApiError && e.status === 401
          ? "로그인이 만료되었습니다. 다시 로그인한 뒤 시도해 주세요."
          : e instanceof ClientApiError
            ? e.message
            : "탈퇴하지 못했습니다. 잠시 후 다시 시도해 주세요.",
      );
      setDeleting(false);
    }
  }

  return (
    <section className="flex flex-col gap-3 rounded-xl border border-red-200 p-4 dark:border-red-900">
      <h2 className="font-semibold">탈퇴(계정 삭제)</h2>
      {!open ? (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">계정과 회사 프로필을 삭제하고 서비스에서 탈퇴합니다.</p>
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="h-10 rounded-lg border border-red-300 px-4 text-sm font-medium text-red-700 hover:bg-red-50 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-950/50"
          >
            탈퇴하기
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-3 text-sm">
          <div className="rounded-lg bg-red-50 px-3 py-2 text-red-800 dark:bg-red-950/50 dark:text-red-200">
            <p className="font-medium">탈퇴하면 되돌릴 수 없습니다.</p>
            <ul className="mt-1 list-inside list-disc">
              <li>로그인 계정({session.user.email})과 회사 프로필, 추천 기록이 삭제됩니다.</li>
              <li>남기신 의견(피드백) 내용은 작성자 정보 없이 익명으로 남습니다.</li>
              <li>같은 Google 계정으로 다시 로그인하면 새 계정으로 시작합니다.</li>
            </ul>
          </div>
          <label className="flex flex-col gap-1.5 font-medium">
            계속하려면 &quot;{CONFIRM_WORD}&quot;를 입력하세요
            <input
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder={CONFIRM_WORD}
              autoComplete="off"
              className="h-10 rounded-lg border border-zinc-300 bg-white px-3 font-normal outline-none focus:border-red-500 dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
          {error && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-red-700 dark:bg-red-950/50 dark:text-red-300">
              {error}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onDelete}
              disabled={!confirmed || deleting}
              className="h-10 rounded-lg bg-red-600 px-4 font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {deleting ? "삭제 중…" : "계정 삭제"}
            </button>
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                setConfirmText("");
                setError(null);
              }}
              disabled={deleting}
              className="h-10 rounded-lg border border-zinc-300 px-4 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900"
            >
              취소
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
