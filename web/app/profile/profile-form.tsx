"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import TagInput from "@/components/tag-input";
import { apiFetch, ClientApiError } from "@/lib/client-api";
import { formatDateTime, formatPrice } from "@/lib/format";
import { getSupabase } from "@/lib/supabase";
import type { Profile, ProfileInput } from "@/lib/types";

const REGION_SUGGESTIONS = ["전국", "서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "세종"];
const INDUSTRY_SUGGESTIONS = ["소프트웨어 개발", "정보시스템 유지보수", "데이터 구축", "컨설팅", "설계·감리"];

const inputClass =
  "h-10 w-full rounded-lg border border-zinc-300 bg-white px-3 text-sm outline-none focus:border-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-400";

interface FormValues {
  company_name: string;
  industries: string[];
  regions: string[];
  min_price: string;
  max_price: string;
  keywords: string[];
}

const EMPTY: FormValues = { company_name: "", industries: [], regions: [], min_price: "", max_price: "", keywords: [] };

function toForm(profile: Profile): FormValues {
  return {
    company_name: profile.company_name ?? "",
    industries: profile.industries,
    regions: profile.regions,
    min_price: profile.min_price?.toString() ?? "",
    max_price: profile.max_price?.toString() ?? "",
    keywords: profile.keywords,
  };
}

function toPrice(text: string): number | null {
  const digits = text.replace(/[^\d]/g, "");
  return digits ? Number(digits) : null;
}

type Loaded = { userId: string; profile: Profile | null } | { userId: string; error: string };
type Notice = { kind: "success" | "error"; text: string } | null;

export default function ProfileForm() {
  const { enabled, loading: authLoading, session, signIn } = useAuth();
  const userId = session?.user.id ?? null;

  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [values, setValues] = useState<FormValues>(EMPTY);
  const [consent, setConsent] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  // 로그인한 사용자가 바뀔 때만 프로필을 불러온다 (토큰 갱신마다 다시 부르지 않음)
  useEffect(() => {
    const supabase = getSupabase();
    if (!userId || !supabase) return;
    let cancelled = false;
    supabase.auth
      .getSession()
      .then(({ data }) => apiFetch<Profile>("/api/me/profile", { token: data.session?.access_token }))
      .then(({ data }) => {
        if (cancelled) return;
        setLoaded({ userId, profile: data });
        setValues(toForm(data));
      })
      .catch((error) => {
        if (cancelled) return;
        if (error instanceof ClientApiError && error.status === 404) {
          setLoaded({ userId, profile: null }); // 아직 프로필 없음 → 작성 화면
          setValues(EMPTY);
        } else {
          setLoaded({ userId, error: error instanceof ClientApiError ? error.message : "프로필을 불러오지 못했습니다." });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  if (!enabled) {
    return <p className="text-sm text-red-600">로그인 설정(Supabase 환경 변수)이 없어 프로필을 쓸 수 없습니다.</p>;
  }
  if (authLoading || (userId && loaded?.userId !== userId)) {
    return <div className="h-64 animate-pulse rounded-xl bg-zinc-100 dark:bg-zinc-900" aria-busy="true" />;
  }
  if (!session || !userId) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-zinc-300 py-12 text-center text-sm dark:border-zinc-700">
        <p>프로필을 저장하려면 로그인이 필요합니다.</p>
        <button
          type="button"
          onClick={() => signIn("/profile")}
          className="h-10 rounded-lg bg-zinc-900 px-4 font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          Google로 로그인
        </button>
      </div>
    );
  }
  if (loaded && "error" in loaded) {
    return (
      <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
        {loaded.error}
      </p>
    );
  }

  const existing = loaded && "profile" in loaded ? loaded.profile : null;
  const isNew = existing === null;
  const minPrice = toPrice(values.min_price);
  const maxPrice = toPrice(values.max_price);
  const priceInverted = minPrice !== null && maxPrice !== null && minPrice > maxPrice;
  const canSave = !saving && !priceInverted && (!isNew || consent);

  const set = <K extends keyof FormValues>(key: K, value: FormValues[K]) => {
    setValues((prev) => ({ ...prev, [key]: value }));
    setNotice(null);
  };

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSave || !userId) return;
    setSaving(true);
    setNotice(null);
    const body: ProfileInput = {
      company_name: values.company_name.trim() || null,
      industries: values.industries,
      regions: values.regions,
      min_price: minPrice,
      max_price: maxPrice,
      keywords: values.keywords,
      consent: isNew ? consent : true, // 처음 저장할 때만 동의 필수 (이후 수정은 api가 최초 동의 시각 유지)
    };
    try {
      const { data } = await apiFetch<Profile>("/api/me/profile", {
        method: "PUT",
        body: JSON.stringify(body),
        token: session?.access_token,
      });
      setLoaded({ userId, profile: data });
      setValues(toForm(data));
      setNotice({ kind: "success", text: "프로필을 저장했습니다." });
    } catch (error) {
      setNotice({
        kind: "error",
        text: error instanceof ClientApiError ? error.message : "저장하지 못했습니다. 잠시 후 다시 시도해 주세요.",
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-5 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      {isNew ? (
        <p className="rounded-lg bg-sky-50 px-3 py-2 text-sm text-sky-800 dark:bg-sky-950/50 dark:text-sky-200">
          아직 저장된 프로필이 없습니다. 아래 내용을 입력해 주세요.
        </p>
      ) : (
        <p className="text-xs text-zinc-500">개인정보 수집·이용 동의: {formatDateTime(existing.consent_at)}</p>
      )}

      <label className="flex flex-col gap-2 text-sm font-medium">
        회사명 (선택)
        <input
          value={values.company_name}
          onChange={(e) => set("company_name", e.target.value)}
          maxLength={100}
          placeholder="예: 예시소프트"
          className={`${inputClass} font-normal`}
        />
      </label>

      <TagInput
        label="업종"
        values={values.industries}
        onChange={(v) => set("industries", v)}
        placeholder="입력 후 Enter (예: 소프트웨어 개발)"
        suggestions={INDUSTRY_SUGGESTIONS}
      />
      <TagInput
        label="지역"
        values={values.regions}
        onChange={(v) => set("regions", v)}
        placeholder="입력 후 Enter (예: 서울)"
        suggestions={REGION_SUGGESTIONS}
      />

      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium">관심 금액 범위 (추정가격, 원)</span>
        <div className="flex items-center gap-2">
          <input
            inputMode="numeric"
            value={values.min_price}
            onChange={(e) => set("min_price", e.target.value.replace(/[^\d]/g, ""))}
            placeholder="최소"
            aria-label="관심 금액 최소"
            className={inputClass}
          />
          <span aria-hidden>~</span>
          <input
            inputMode="numeric"
            value={values.max_price}
            onChange={(e) => set("max_price", e.target.value.replace(/[^\d]/g, ""))}
            placeholder="최대"
            aria-label="관심 금액 최대"
            className={inputClass}
          />
        </div>
        <p className={`text-xs ${priceInverted ? "text-red-600 dark:text-red-400" : "text-zinc-500"}`}>
          {priceInverted
            ? "최소 금액이 최대 금액보다 큽니다."
            : `${minPrice !== null ? formatPrice(minPrice) : "제한 없음"} ~ ${maxPrice !== null ? formatPrice(maxPrice) : "제한 없음"}`}
        </p>
      </div>

      <TagInput
        label="관심 키워드"
        values={values.keywords}
        onChange={(v) => set("keywords", v)}
        placeholder="입력 후 Enter (예: GIS, 데이터베이스)"
      />

      {isNew && (
        <section className="flex flex-col gap-3 rounded-lg border border-zinc-200 p-3 text-sm dark:border-zinc-800">
          <h2 className="font-semibold">개인정보 수집·이용 동의 (필수)</h2>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-zinc-700 dark:text-zinc-300">
            <dt className="text-zinc-500">수집 항목</dt>
            <dd>이메일(Google 로그인 계정), 회사 프로필(회사명, 업종, 지역, 관심 금액 범위, 관심 키워드)</dd>
            <dt className="text-zinc-500">이용 목적</dt>
            <dd>회사에 맞는 입찰공고 추천과 적합도 판단, 서비스 개선</dd>
            <dt className="text-zinc-500">보유 기간</dt>
            <dd>
              탈퇴할 때까지(또는 과제 운영 종료 시). 이 화면 아래 &quot;탈퇴(계정 삭제)&quot;로 언제든 계정과 프로필을 삭제할
              수 있으며, 남기신 의견(피드백) 내용은 작성자 정보 없이 익명으로 남습니다.
            </dd>
          </dl>
          <p className="text-xs text-zinc-500">동의하지 않으면 프로필을 저장할 수 없습니다. 공고 조회는 동의 없이도 쓸 수 있습니다.</p>
          <label className="flex items-center gap-2 font-medium">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="h-4 w-4" />
            위 내용을 확인했고 개인정보 수집·이용에 동의합니다.
          </label>
        </section>
      )}

      {notice && (
        <p
          role={notice.kind === "error" ? "alert" : "status"}
          className={`rounded-lg px-3 py-2 text-sm ${
            notice.kind === "error"
              ? "bg-red-50 text-red-700 dark:bg-red-950/50 dark:text-red-300"
              : "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200"
          }`}
        >
          {notice.text}
        </p>
      )}

      <button
        type="submit"
        disabled={!canSave}
        className="h-11 rounded-lg bg-zinc-900 text-sm font-medium text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
      >
        {saving ? "저장 중…" : isNew ? "동의하고 저장" : "저장"}
      </button>
    </form>
  );
}
