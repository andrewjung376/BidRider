"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// 지금 보고 있는 화면 경로를 피드백과 함께 보내도록 ?from= 으로 넘긴다
export default function FeedbackLink({ className, children }: { className?: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const href = pathname === "/feedback" ? "/feedback" : `/feedback?from=${encodeURIComponent(pathname)}`;
  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}
