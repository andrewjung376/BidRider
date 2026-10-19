import type { Metadata } from "next";
import ChatPanel from "./chat-panel";

export const metadata: Metadata = { title: "AI 공고 검색" };

export default function ChatPage() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-bold tracking-tight">AI 공고 검색</h1>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        원하는 조건을 문장으로 물어보세요. AI가 수집된 공고를 검색해 답하고, 근거가 된 공고를 함께 보여 줍니다. 회사
        프로필을 저장했다면 답변에 반영합니다.
      </p>
      <ChatPanel />
    </main>
  );
}
