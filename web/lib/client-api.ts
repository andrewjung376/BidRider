// 브라우저에서 api를 호출한다 (/api/* 는 next.config.ts rewrites가 FastAPI로 프록시).
// 로그인 상태면 Authorization: Bearer <Supabase access_token> 을 붙인다 (계약서 1장).

export class ClientApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ClientApiError";
  }
}

/** FastAPI 오류 응답({"detail": "..."} 또는 422의 [{loc, msg}])에서 사람이 읽을 메시지를 꺼낸다 */
function detailMessage(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (status === 422) return "입력값을 확인해 주세요.";
  if (status === 401) return "로그인이 필요합니다.";
  return `요청을 처리하지 못했습니다. (${status})`;
}

export async function apiFetch<T>(
  path: string,
  { token, ...init }: RequestInit & { token?: string | null } = {},
): Promise<{ status: number; data: T }> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  // 잘못된 토큰은 401이므로, 토큰이 없을 때는 헤더 자체를 보내지 않는다
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(path, { ...init, headers });
  } catch {
    throw new ClientApiError(0, "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ClientApiError(res.status, detailMessage(res.status, body));
  return { status: res.status, data: body as T };
}
