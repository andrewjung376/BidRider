import { closingLabel } from "@/lib/format";

// 입찰마감까지 남은 날짜 (마감 3일 이내는 강조)
export default function ClosingBadge({ iso }: { iso: string | null }) {
  const label = closingLabel(iso);
  if (!label) return null;
  const color = label.urgent
    ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
    : label.text === "마감"
      ? "bg-zinc-200 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
      : "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300";
  return <span className={`rounded-full px-2 py-0.5 font-medium ${color}`}>{label.text}</span>;
}
