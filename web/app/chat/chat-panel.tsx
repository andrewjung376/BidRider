"use client";

import { useEffect, useRef, useState } from "react";
import AiBadge from "@/components/ai-badge";
import { useAuth } from "@/components/auth-provider";
import BidCard from "@/components/bid-card";
import { useElapsedSeconds } from "@/components/use-elapsed";
import { apiFetch, ClientApiError } from "@/lib/client-api";
import { formatPrice } from "@/lib/format";
import type { ChatResponse, ChatTurn, ToolCall } from "@/lib/types";

// 계약서 3.4: message 1~1000자, history 최대 10개·content 1~4000자, 응답 최대 약 30초(제한 60초 이상)
const MAX_MESSAGE = 1000;
const MAX_HISTORY = 10;
const MAX_HISTORY_CONTENT = 4000;
const CHAT_TIMEOUT_MS = 90_000;

const EXAMPLES = [
  "이번 주에 마감하는 설계 용역 공고 찾아줘",
  "1억 이하 경기 지역 기관 공고 있어?",
  "GIS나 데이터베이스 관련 공고 알려줘",
];

// 이벤트 처리 중에만 부르는 현재 시각 (렌더링 중 호출 아님)
const nowMs = () => Date.now();

type Message ={ role: "user"; content: string } | { role: "assistant"; content: string; response: ChatResponse };

/** 이전 대화를 history로 만든다: 최근 10개, 각 내용은 4000자 이내 (긴 답변을 그대로 보내면 422) */
function toHistory(messages: Message[]): ChatTurn[] {
  return messages
    .slice(-MAX_HISTORY)
    .map((m) => ({ role: m.role, content: m.content.slice(0, MAX_HISTORY_CONTENT) }));
}

const ARG_LABELS: Record<string, string> = {
  category: "업무 구분",
  q: "키워드",
  institution: "기관",
  min_price: "최소 금액",
  max_price: "최대 금액",
  closing_from: "마감일 시작",
  closing_to: "마감일 끝",
  bid_id: "공고 ID",
  page: "페이지",
  size: "건수",
};
const TOOL_LABELS: Record<string, string> = { search_bids: "공고 검색", get_bid_detail: "공고 상세 조회" };

function formatArg(key: string, value: unknown): string {
  if ((key === "min_price" || key === "max_price") && typeof value === "number") return formatPrice(value);
  return typeof value === "string" ? value : JSON.stringify(value);
}

function ToolCalls({ calls }: { calls: ToolCall[] }) {
  if (calls.length === 0) return null;
  return (
    <details className="text-xs text-zinc-500">
      <summary className="cursor-pointer select-none">검색 조건 보기 ({calls.length})</summary>
      <ol className="mt-2 flex flex-col gap-1.5">
        {calls.map((call, i) => (
          <li key={i} className="rounded-lg bg-zinc-100 px-3 py-2 dark:bg-zinc-900">
            <span className="font-medium text-zinc-700 dark:text-zinc-300">{TOOL_LABELS[call.name] ?? call.name}</span>
            {call.result_count !== null && <span> · 결과 {call.result_count}건</span>}
            {Object.keys(call.args).length > 0 && (
              <span className="block break-all">
                {Object.entries(call.args)
                  .map(([k, v]) => `${ARG_LABELS[k] ?? k}: ${formatArg(k, v)}`)
                  .join(" · ")}
              </span>
            )}
          </li>
        ))}
      </ol>
    </details>
  );
}

export default function ChatPanel() {
  const { enabled, loading: authLoading, session, signIn } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const elapsed = useElapsedSeconds(startedAt);
  const bottomRef = useRef<HTMLDivElement>(null);
  const sending = startedAt !== null;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  if (!enabled) {
    return <p className="text-sm text-red-600">로그인 설정(Supabase 환경 변수)이 없어 AI 검색을 쓸 수 없습니다.</p>;
  }
  if (authLoading) {
    return <div className="h-40 animate-pulse rounded-xl bg-zinc-100 dark:bg-zinc-900" aria-busy="true" />;
  }
  if (!session) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-zinc-300 py-12 text-center text-sm dark:border-zinc-700">
        <p>AI 공고 검색은 로그인 후 쓸 수 있습니다.</p>
        <button
          type="button"
          onClick={() => signIn("/chat")}
          className="h-10 rounded-lg bg-zinc-900 px-4 font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          Google로 로그인
        </button>
      </div>
    );
  }

  const trimmed = input.trim();
  const canSend = trimmed.length > 0 && trimmed.length <= MAX_MESSAGE && !sending;

  async function send(text: string) {
    const message = text.trim();
    if (!message || message.length > MAX_MESSAGE || sending) return;
    const history = toHistory(messages);
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    setError(null);
    setStartedAt(nowMs());
    try {
      const { data } = await apiFetch<ChatResponse>("/api/agent/chat", {
        method: "POST",
        body: JSON.stringify({ message, history }),
        token: session?.access_token,
        signal: AbortSignal.timeout(CHAT_TIMEOUT_MS),
      });
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer, response: data }]);
    } catch (e) {
      // 실패한 질문은 대화에서 빼고 입력창에 되돌려 다시 보낼 수 있게 한다
      setMessages((prev) => prev.slice(0, -1));
      setInput(message);
      setError(
        e instanceof ClientApiError && e.timedOut
          ? "응답이 늦어 기다리기를 멈췄습니다. 잠시 후 다시 시도해 주세요."
          : e instanceof ClientApiError && e.status === 401
            ? "로그인이 만료되었습니다. 다시 로그인한 뒤 시도해 주세요."
            : e instanceof ClientApiError
              ? e.message
              : "답변을 받지 못했습니다. 잠시 후 다시 시도해 주세요.",
      );
    } finally {
      setStartedAt(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {messages.length === 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-zinc-500">예시 질문</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => send(example)}
                disabled={sending}
                className="rounded-full border border-zinc-300 px-3 py-1.5 text-left text-sm hover:border-zinc-500 disabled:opacity-40 dark:border-zinc-700"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}

      <ol className="flex flex-col gap-4" aria-live="polite">
        {messages.map((m, i) =>
          m.role === "user" ? (
            <li key={i} className="self-end max-w-[85%] rounded-2xl rounded-br-sm bg-zinc-900 px-4 py-2.5 text-sm whitespace-pre-line text-white dark:bg-zinc-100 dark:text-zinc-900">
              {m.content}
            </li>
          ) : (
            <li key={i} className="flex flex-col gap-3">
              <div className="flex flex-col gap-2 rounded-2xl rounded-bl-sm border border-violet-200 bg-violet-50/50 px-4 py-3 dark:border-violet-900 dark:bg-violet-950/30">
                <div className="flex items-center gap-2">
                  <AiBadge />
                  <span className="text-xs text-zinc-500">{m.response.model}</span>
                </div>
                <p className="text-sm leading-relaxed whitespace-pre-line">{m.content}</p>
                <ToolCalls calls={m.response.tool_calls} />
              </div>
              {m.response.bids.length > 0 && (
                <div className="flex flex-col gap-2">
                  <p className="text-xs text-zinc-500">근거 공고 {m.response.bids.length}건 · 원문은 각 공고 상세에서 확인하세요</p>
                  <ul className="flex flex-col gap-3">
                    {m.response.bids.map((bid) => (
                      <BidCard key={bid.id} bid={bid} />
                    ))}
                  </ul>
                </div>
              )}
            </li>
          ),
        )}
        {sending && (
          <li className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />
            AI가 공고를 찾는 중… {elapsed}초 (보통 10초 안팎, 최대 30초)
          </li>
        )}
      </ol>
      <div ref={bottomRef} />

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
          {error}
        </p>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="sticky bottom-0 flex flex-col gap-2 rounded-xl border border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-950"
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            // Enter로 보내기, Shift+Enter는 줄바꿈 (한글 조합 중에는 보내지 않음)
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              send(input);
            }
          }}
          rows={2}
          maxLength={MAX_MESSAGE}
          placeholder="예: 서울 SW 개발 1억 이하, 이번 주 마감 공고 찾아줘"
          aria-label="질문"
          className="resize-none bg-transparent text-sm outline-none"
        />
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-zinc-500 tabular-nums">
            {input.length.toLocaleString("ko-KR")} / {MAX_MESSAGE.toLocaleString("ko-KR")}
          </span>
          <div className="flex gap-2">
            {messages.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  setMessages([]);
                  setError(null);
                }}
                disabled={sending}
                className="h-9 rounded-lg border border-zinc-300 px-3 text-sm hover:bg-zinc-100 disabled:opacity-40 dark:border-zinc-700 dark:hover:bg-zinc-900"
              >
                새 대화
              </button>
            )}
            <button
              type="submit"
              disabled={!canSend}
              className="h-9 rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
            >
              {sending ? "답변 중…" : "보내기"}
            </button>
          </div>
        </div>
      </form>
      <p className="text-xs text-zinc-500">
        대화는 저장되지 않아 새로고침하면 사라집니다. AI 답변은 참고용이며, 입찰 참여 전 나라장터 원문을 확인하세요.
      </p>
    </div>
  );
}
