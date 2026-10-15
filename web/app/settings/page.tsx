import type { Metadata } from "next";
import { fetchSettings } from "@/lib/api";
import SettingsPanel from "./settings-panel";

export const metadata: Metadata = { title: "수집 설정" };

export default async function SettingsPage() {
  const settings = await fetchSettings();

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-bold tracking-tight">수집 설정</h1>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        매일 오전 9시 정기 수집과 &quot;지금 수집&quot;이 가져올 업무 구분과 건수를 정합니다. 설정은 서비스 전체에
        적용됩니다.
      </p>
      <SettingsPanel initial={settings} />
    </main>
  );
}
