"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

// 탈퇴 후 홈으로 돌아왔을 때(/?account=deleted) 완료 안내
export default function AccountNotice() {
  const params = useSearchParams();
  if (params.get("account") !== "deleted") return null;

  return (
    <div
      role="status"
      className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200"
    >
      <span>탈퇴가 완료되었습니다. 계정과 회사 프로필이 삭제되었습니다. 이용해 주셔서 감사합니다.</span>
      <Link href="/" className="underline underline-offset-4">
        닫기
      </Link>
    </div>
  );
}
