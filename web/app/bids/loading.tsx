export default function Loading() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-3 px-4 py-6 sm:px-6" aria-busy="true">
      <p className="sr-only">공고를 불러오는 중입니다.</p>
      {Array.from({ length: 4 }, (_, i) => (
        <div key={i} className="h-32 animate-pulse rounded-xl bg-zinc-100 dark:bg-zinc-900" />
      ))}
    </main>
  );
}
