-- BidRadar 초기 스키마와 RLS
-- 기준: doc/data-contract.md v1 (2026-10-16) 2장
-- 담당: 팀원 (Frontend / Data / QA)

-- =========================================================
-- 2.1 확장
-- =========================================================
-- 한국어 공고명 부분 검색(ILIKE)용 트라이그램 인덱스
create extension if not exists pg_trgm with schema extensions;

-- =========================================================
-- 공통: updated_at 자동 갱신 트리거 함수
-- =========================================================
create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- =========================================================
-- 2.2 bids — 입찰공고
-- =========================================================
create table public.bids (
  id               bigint generated always as identity primary key,
  bid_ntce_no      text        not null,
  bid_ntce_ord     text        not null default '000',
  category         text        not null check (category in ('용역', '공사', '물품', '외자')),
  bid_ntce_nm      text        not null,
  ntce_instt_nm    text,
  dminstt_nm       text,
  presmpt_prce     bigint,
  bid_ntce_dt      timestamptz,
  bid_clse_dt      timestamptz,
  openg_dt         timestamptz,
  bid_ntce_dtl_url text,
  raw              jsonb       not null,
  collected_at     timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  constraint bids_ntce_no_ord_key unique (bid_ntce_no, bid_ntce_ord)
);

create index bids_bid_ntce_dt_idx on public.bids (bid_ntce_dt desc);
create index bids_category_idx    on public.bids (category);
create index bids_bid_clse_dt_idx on public.bids (bid_clse_dt);
create index bids_bid_ntce_nm_trgm_idx on public.bids using gin (bid_ntce_nm extensions.gin_trgm_ops);

create trigger bids_set_updated_at
  before update on public.bids
  for each row execute function public.set_updated_at();

-- =========================================================
-- 2.3 bid_summaries — AI 요약 (FR-04)
-- =========================================================
create table public.bid_summaries (
  bid_id             bigint      primary key references public.bids (id) on delete cascade,
  summary            text        not null,
  qualifications     text,
  required_documents jsonb       not null default '[]'::jsonb,
  provider           text        not null,
  model              text        not null,
  created_at         timestamptz not null default now()
);

-- =========================================================
-- 2.4 collect_settings — 수집 설정 (FR-14, 서비스 전체 1행)
-- =========================================================
create table public.collect_settings (
  id         smallint    primary key default 1 check (id = 1),
  categories text[]      not null default '{용역}'
             check (
               cardinality(categories) >= 1
               and categories <@ array['용역', '공사', '물품', '외자']::text[]
             ),
  num_rows   int         not null default 10 check (num_rows between 1 and 100),
  updated_by uuid        references auth.users (id) on delete set null,
  updated_at timestamptz not null default now()
);

create trigger collect_settings_set_updated_at
  before update on public.collect_settings
  for each row execute function public.set_updated_at();

-- 기본 1행
insert into public.collect_settings (id) values (1);

-- =========================================================
-- 2.5 collect_runs — 수집 실행 기록 (NFR-02)
-- =========================================================
create table public.collect_runs (
  id             bigint generated always as identity primary key,
  trigger        text        not null check (trigger in ('cron', 'manual')),
  categories     text[]      not null,
  status         text        not null check (status in ('running', 'success', 'failed')),
  fetched_count  int         not null default 0,
  inserted_count int         not null default 0,
  error          text,
  requested_by   uuid        references auth.users (id) on delete set null,
  started_at     timestamptz not null default now(),
  finished_at    timestamptz
);

-- =========================================================
-- 2.6 profiles — 회사 프로필 (FR-05, Long-term Memory)
-- =========================================================
create table public.profiles (
  user_id      uuid        primary key references auth.users (id) on delete cascade,
  company_name text,
  industries   text[]      not null default '{}',
  regions      text[]      not null default '{}',
  min_price    bigint,
  max_price    bigint,
  keywords     text[]      not null default '{}',
  consent_at   timestamptz not null,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- =========================================================
-- 2.7 recommendations — 적합도 추천과 피드백 (FR-06·08)
-- =========================================================
create table public.recommendations (
  user_id    uuid        not null references auth.users (id) on delete cascade,
  bid_id     bigint      not null references public.bids (id) on delete cascade,
  score      int         not null check (score between 0 and 100),
  reason     text        not null,
  feedback   smallint    check (feedback in (-1, 1)),
  model      text        not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, bid_id)
);

create index recommendations_bid_id_idx on public.recommendations (bid_id);

create trigger recommendations_set_updated_at
  before update on public.recommendations
  for each row execute function public.set_updated_at();

-- =========================================================
-- 2.8 feedbacks — 사용자 테스트 피드백 (FR-11)
-- =========================================================
create table public.feedbacks (
  id         bigint generated always as identity primary key,
  user_id    uuid        references auth.users (id) on delete set null,
  rating     smallint    not null check (rating between 1 and 5),
  message    text        not null,
  page       text,
  created_at timestamptz not null default now()
);

-- =========================================================
-- 2.9 RLS
-- api는 service role 키로 접근해 RLS를 우회한다.
-- 아래 정책은 키 노출이나 web의 실수로 인한 직접 접근을 막는 방어선이다.
-- =========================================================
alter table public.bids             enable row level security;
alter table public.bid_summaries    enable row level security;
alter table public.collect_settings enable row level security;
alter table public.collect_runs     enable row level security;
alter table public.profiles         enable row level security;
alter table public.recommendations  enable row level security;
alter table public.feedbacks        enable row level security;

-- bids, bid_summaries: 공공데이터라 anon·authenticated 모두 조회 허용
create policy "bids_select_all" on public.bids
  for select to anon, authenticated
  using (true);

create policy "bid_summaries_select_all" on public.bid_summaries
  for select to anon, authenticated
  using (true);

-- collect_settings, collect_runs, feedbacks: 정책 없음 (api 경유만 허용)

-- profiles: 본인 행만
create policy "profiles_select_own" on public.profiles
  for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "profiles_insert_own" on public.profiles
  for insert to authenticated
  with check ((select auth.uid()) = user_id);

create policy "profiles_update_own" on public.profiles
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "profiles_delete_own" on public.profiles
  for delete to authenticated
  using ((select auth.uid()) = user_id);

-- recommendations: 본인 행만
create policy "recommendations_select_own" on public.recommendations
  for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "recommendations_insert_own" on public.recommendations
  for insert to authenticated
  with check ((select auth.uid()) = user_id);

create policy "recommendations_update_own" on public.recommendations
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "recommendations_delete_own" on public.recommendations
  for delete to authenticated
  using ((select auth.uid()) = user_id);
