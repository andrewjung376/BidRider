"use client";

import type { Session } from "@supabase/supabase-js";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getSupabase, isAuthConfigured } from "@/lib/supabase";

interface AuthState {
  /** 로그인 기능을 쓸 수 있는지 (Supabase 환경 변수 설정 여부) */
  enabled: boolean;
  /** 세션을 확인하는 중 */
  loading: boolean;
  session: Session | null;
  /** Google 로그인. 로그인 후 지금 보던 경로(또는 next)로 돌아온다 */
  signIn: (next?: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const enabled = isAuthConfigured;
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(enabled);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) return;
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });
    // 로그인·로그아웃·토큰 갱신을 따라간다
    const { data } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      setLoading(false);
    });
    return () => data.subscription.unsubscribe();
  }, []);

  const signIn = useCallback(async (next?: string) => {
    const supabase = getSupabase();
    if (!supabase) return;
    const path = next ?? window.location.pathname + window.location.search;
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}${path}` },
    });
  }, []);

  const signOut = useCallback(async () => {
    await getSupabase()?.auth.signOut();
  }, []);

  const value = useMemo(() => ({ enabled, loading, session, signIn, signOut }), [enabled, loading, session, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth는 AuthProvider 안에서만 쓸 수 있습니다.");
  return value;
}
