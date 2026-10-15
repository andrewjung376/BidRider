// 표시 형식: 금액은 원 단위 정수(null이면 "-"), 시각은 한국 시간(KST) 기준

const TIME_ZONE = "Asia/Seoul";

export function formatPrice(value: number | null): string {
  return value === null ? "-" : `${value.toLocaleString("ko-KR")}원`;
}

const dateTimeFormat = new Intl.DateTimeFormat("ko-KR", {
  timeZone: TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

/** "2026-10-27 10:00" (KST). 값이 없으면 "-" */
export function formatDateTime(iso: string | null): string {
  if (!iso) return "-";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "-";
  const part = Object.fromEntries(dateTimeFormat.formatToParts(date).map((p) => [p.type, p.value]));
  return `${part.year}-${part.month}-${part.day} ${part.hour}:${part.minute}`;
}

/** "2026-10-27" (KST) */
export function formatDate(iso: string | null): string {
  return formatDateTime(iso).split(" ")[0];
}

const DAY_MS = 24 * 60 * 60 * 1000;

function kstDayNumber(date: Date): number {
  const ymd = formatDate(date.toISOString());
  return Date.parse(`${ymd}T00:00:00Z`) / DAY_MS;
}

/** 입찰마감까지 남은 상태. 지난 공고는 "마감", 당일은 "D-day", 그 외 "D-3" */
export function closingLabel(iso: string | null, now: Date = new Date()): { text: string; urgent: boolean } | null {
  if (!iso) return null;
  const close = new Date(iso);
  if (Number.isNaN(close.getTime())) return null;
  if (close.getTime() <= now.getTime()) return { text: "마감", urgent: false };
  const days = kstDayNumber(close) - kstDayNumber(now);
  if (days <= 0) return { text: "D-day", urgent: true };
  return { text: `D-${days}`, urgent: days <= 3 };
}
