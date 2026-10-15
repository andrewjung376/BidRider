import type { Metadata } from "next";
// 한글 글꼴: Pretendard 가변 글꼴, 글자 범위별 분할(dynamic subset)로 화면에 쓰인 글자의 파일만 내려받는다
import "pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css";
import "./globals.css";
import SiteHeader from "@/components/site-header";

export const metadata: Metadata = {
  title: {
    default: "BidRadar 입찰레이더",
    template: "%s | BidRadar",
  },
  description: "나라장터 입찰공고 AI 수집·분석 서비스",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
