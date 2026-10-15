"use client";

import { useId, useState } from "react";

const MAX_TAG_LENGTH = 30;

// 여러 값을 입력받는 칸. Enter·쉼표로 추가하고, 칩의 × 로 지운다
export default function TagInput({
  label,
  values,
  onChange,
  placeholder,
  suggestions = [],
  max = 20,
}: {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  suggestions?: string[];
  max?: number;
}) {
  const id = useId();
  const [draft, setDraft] = useState("");

  function add(raw: string) {
    const next = [...values];
    for (const part of raw.split(",")) {
      const value = part.trim().slice(0, MAX_TAG_LENGTH);
      if (value && !next.includes(value) && next.length < max) next.push(value);
    }
    onChange(next);
    setDraft("");
  }

  const remaining = suggestions.filter((s) => !values.includes(s));

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {values.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {values.map((value) => (
            <li
              key={value}
              className="inline-flex items-center gap-1 rounded-full bg-zinc-100 py-1 pr-1 pl-3 text-sm dark:bg-zinc-800"
            >
              {value}
              <button
                type="button"
                onClick={() => onChange(values.filter((v) => v !== value))}
                aria-label={`${value} 지우기`}
                className="inline-flex h-5 w-5 items-center justify-center rounded-full text-zinc-500 hover:bg-zinc-200 hover:text-zinc-900 dark:hover:bg-zinc-700 dark:hover:text-zinc-100"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <input
        id={id}
        value={draft}
        onChange={(e) => {
          const text = e.target.value;
          if (text.includes(",")) add(text);
          else setDraft(text);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.nativeEvent.isComposing) {
            e.preventDefault();
            add(draft);
          }
        }}
        onBlur={() => draft.trim() && add(draft)}
        disabled={values.length >= max}
        placeholder={values.length >= max ? `최대 ${max}개까지 입력할 수 있습니다` : placeholder}
        className="h-10 rounded-lg border border-zinc-300 bg-white px-3 text-sm outline-none focus:border-zinc-500 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-400"
      />
      {remaining.length > 0 && values.length < max && (
        <div className="flex flex-wrap gap-1.5" aria-label={`${label} 추천`}>
          {remaining.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => add(s)}
              className="rounded-full border border-dashed border-zinc-300 px-2.5 py-0.5 text-xs text-zinc-600 hover:border-zinc-500 hover:text-zinc-950 dark:border-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-50"
            >
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
