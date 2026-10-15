import { createClient, type SupabaseClient } from "@supabase/supabase-js";

// web의 Supabase 클라이언트는 로그인(Auth)에만 쓴다. 데이터는 모두 FastAPI(/api/*)를 거친다 (계약서 1장).
// NEXT_PUBLIC_SUPABASE_ANON_KEY는 공개용 publishable 키만 넣는다 (service role 키 금지).
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

/** 로그인 기능을 쓸 수 있는지 (NEXT_PUBLIC_* 는 빌드 시점에 값이 들어간다) */
export const isAuthConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);

let client: SupabaseClient | null = null;

/** 브라우저 전용 Supabase 클라이언트. 환경 변수가 없으면 null (로그인 기능만 꺼진다). */
export function getSupabase(): SupabaseClient | null {
  if (typeof window === "undefined" || !SUPABASE_URL || !SUPABASE_ANON_KEY) return null;
  client ??= createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: {
      flowType: "pkce", // Google에서 돌아온 ?code= 를 세션으로 바꾼다
      detectSessionInUrl: true,
      persistSession: true,
      autoRefreshToken: true,
    },
  });
  return client;
}
