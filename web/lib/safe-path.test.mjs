// npm test (node --experimental-strip-types --test): parseSafePath 오픈 리다이렉트 방지 검사
import assert from "node:assert/strict";
import { test } from "node:test";
import { MAX_PAGE_LENGTH, parseSafePath } from "./safe-path.ts";

// 입력은 searchParams가 한 번 디코딩한 값 기준. %2e(.)는 URL 해석이 . 으로 보고 정리하므로 그대로도 검사한다
const REJECTED = [
  ["역슬래시", "/\\evil.com"],
  ["프로토콜 상대 주소", "//evil.com"],
  ["절대 주소", "https://evil.com"],
  ["javascript: 스킴", "javascript:alert(1)"],
  ["/로 시작하지 않음", "bids"],
  ["탭", "/\t/evil.com"],
  ["줄바꿈", "/\n/evil.com"],
  ["NUL", "/\u0000/evil.com"],
  ["DEL", "/\u007f/evil.com"],
  ["정리 후 // (.)", "/.//evil.com"],
  ["정리 후 // (..)", "/x/..//evil.com"],
  ["정리 후 // (%2e)", "/%2e//evil.com"],
  ["정리 후 // (%2e%2e)", "/%2e%2e//evil.com"],
  ["정리 후 // (상위로 여러 번)", "/a/b/../..//evil.com"],
  ["빈 값", ""],
  ["없음", undefined],
];

const ACCEPTED = [
  ["목록", "/bids", "/bids"],
  ["쿼리 유지", "/bids?q=GIS", "/bids?q=GIS"],
  ["상세", "/bids/5", "/bids/5"],
  ["./ 정리", "/./bids", "/bids"],
  [".. 정리", "/x/../bids", "/bids"],
  ["루트", "/", "/"],
  ["인코딩된 슬래시는 그대로", "/%2F%2Fevil.com", "/%2F%2Fevil.com"],
  ["한글 쿼리", "/bids?q=설계", "/bids?q=%EC%84%A4%EA%B3%84"],
];

for (const [name, input] of REJECTED) {
  test(`거부: ${name} (${JSON.stringify(input)})`, () => {
    assert.equal(parseSafePath(input), null);
  });
}

for (const [name, input, expected] of ACCEPTED) {
  test(`허용: ${name} (${input})`, () => {
    assert.equal(parseSafePath(input), expected);
  });
}

test("배열이면 첫 번째 값만 검사", () => {
  assert.equal(parseSafePath(["/bids", "//evil.com"]), "/bids");
  assert.equal(parseSafePath(["//evil.com", "/bids"]), null);
});

test(`${MAX_PAGE_LENGTH}자로 자름`, () => {
  const long = "/" + "a".repeat(MAX_PAGE_LENGTH + 50);
  assert.equal(parseSafePath(long)?.length, MAX_PAGE_LENGTH);
});

test("허용된 결과는 항상 /로 시작하고 //로 시작하지 않음", () => {
  for (const [, input] of [...REJECTED, ...ACCEPTED]) {
    const result = parseSafePath(input);
    if (result !== null) {
      assert.ok(result.startsWith("/") && !result.startsWith("//"), `${JSON.stringify(input)} → ${result}`);
    }
  }
});
