// 사용자가 넘긴 경로(?from= 등)를 이 서비스 안의 경로로만 받기 위한 검사 (오픈 리다이렉트 방지)

export const MAX_PAGE_LENGTH = 200; // api FeedbackIn.page 최대 길이

const SAME_ORIGIN = "http://local";
// 역슬래시는 브라우저가 "/"로 바꿔 읽고(/\evil.com → //evil.com), 탭·줄바꿈은 URL 해석 때 지워진다
const UNSAFE_CHARS = /[\\\u0000-\u001f\u007f]/;

/**
 * 같은 출처의 경로(pathname + search)만 돌려주고, 아니면 null.
 * 결과는 화면 표시, 피드백의 page 저장, 링크 href에 그대로 쓰인다.
 */
export function parseSafePath(value: string | string[] | undefined): string | null {
  const text = Array.isArray(value) ? value[0] : value;
  if (!text || !text.startsWith("/") || UNSAFE_CHARS.test(text)) return null;
  let url: URL;
  try {
    url = new URL(text, SAME_ORIGIN);
  } catch {
    return null;
  }
  if (url.origin !== SAME_ORIGIN) return null;
  // URL 해석이 . / .. 를 정리하므로 결과가 //로 시작할 수 있다 (/.//evil.com → //evil.com)
  const path = url.pathname + url.search;
  if (path.startsWith("//")) return null;
  return path.slice(0, MAX_PAGE_LENGTH);
}
