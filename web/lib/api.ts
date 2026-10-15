import { connection } from "next/server";
import { cache } from "react";
import {
  CATEGORIES,
  type BidDetail,
  type BidList,
  type BidQuery,
  type Category,
  type CollectSettings,
} from "./types";

// 서버 컴포넌트에서 api를 직접 호출한다 (브라우저의 /api/* 요청은 next.config.ts rewrites가 프록시).
// rewrites와 달리 이 값은 실행 시점에 읽는다.
const API_BASE_URL = (process.env.API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");

export const PAGE_SIZE = 20;

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function getJson<T>(path: string): Promise<T> {
  // api 데이터는 요청마다 새로 읽는다 (빌드 시점에 미리 렌더링하지 않음)
  await connection();
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  } catch {
    throw new ApiError(0, "api 서버에 연결할 수 없습니다.");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body?.detail ?? `api 오류 (${res.status})`);
  }
  return res.json() as Promise<T>;
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const INT_RE = /^\d+$/;

/** searchParams에서 계약서에 있는 필터만 골라 형식을 검증한다. 잘못된 값은 버린다. */
export function parseBidQuery(params: Record<string, string | string[] | undefined>): BidQuery {
  const get = (key: string) => {
    const value = params[key];
    const text = (Array.isArray(value) ? value[0] : value)?.trim();
    return text ? text : undefined;
  };
  const query: BidQuery = {};

  const category = get("category");
  if (category && (CATEGORIES as readonly string[]).includes(category)) query.category = category as Category;

  const q = get("q");
  if (q) query.q = q;
  const institution = get("institution");
  if (institution) query.institution = institution;

  for (const key of ["min_price", "max_price"] as const) {
    const value = get(key)?.replace(/,/g, "");
    if (value && INT_RE.test(value)) query[key] = value;
  }
  for (const key of ["closing_from", "closing_to"] as const) {
    const value = get(key);
    if (value && DATE_RE.test(value)) query[key] = value;
  }

  const page = get("page");
  if (page && INT_RE.test(page) && Number(page) >= 1) query.page = page;
  return query;
}

/** 필터를 쿼리 문자열로 만든다. 빈 값은 넣지 않는다. */
export function toSearchParams(query: BidQuery): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value) params.set(key, value);
  }
  return params;
}

export async function fetchBids(query: BidQuery): Promise<BidList> {
  const params = toSearchParams(query);
  params.set("size", String(PAGE_SIZE));
  return getJson<BidList>(`/api/bids?${params}`);
}

export async function fetchSettings(): Promise<CollectSettings> {
  return getJson<CollectSettings>("/api/settings");
}

/** 공고 상세. 없으면 null. generateMetadata와 페이지가 같은 요청을 공유하도록 cache로 감싼다. */
export const fetchBid = cache(async (id: string): Promise<BidDetail | null> => {
  if (!INT_RE.test(id)) return null;
  try {
    return await getJson<BidDetail>(`/api/bids/${id}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
});
