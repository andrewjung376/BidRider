import type { Metadata } from "next";
import ProfileForm from "./profile-form";

export const metadata: Metadata = { title: "회사 프로필" };

export default function ProfilePage() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-bold tracking-tight">회사 프로필</h1>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        업종·지역·금액 범위·관심 키워드를 저장하면 회사에 맞는 공고를 추천하는 데 씁니다.
      </p>
      <ProfileForm />
    </main>
  );
}
