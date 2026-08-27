// @ts-check
/** 파이썬 str 메서드와 같은 뜻의 문자열 도우미. 두 구현의 결과가 글자 단위로 같아야 해서 따로 둔다. */

/**
 * 파이썬 str.splitlines(). 끝의 빈 줄을 만들지 않는다.
 * @param {string} text
 */
export function splitLines(text) {
  if (text === "") return [];
  const lines = text.split(/\r\n|\r|\n/);
  if (lines[lines.length - 1] === "") lines.pop();
  return lines;
}

/** 파이썬 str.split() (인자 없음). 공백 덩어리로 나누고 빈 것은 버린다. @param {string} text */
export function splitWords(text) {
  return text.split(/\s+/).filter((word) => word.length > 0);
}

/** 파이썬 str.strip(chars). @param {string} text @param {string} chars */
export function stripChars(text, chars) {
  let start = 0;
  let end = text.length;
  while (start < end && chars.includes(text[start])) start++;
  while (end > start && chars.includes(text[end - 1])) end--;
  return text.slice(start, end);
}

/** 파이썬 str.rstrip(chars). @param {string} text @param {string} chars */
export function rstripChars(text, chars) {
  let end = text.length;
  while (end > 0 && chars.includes(text[end - 1])) end--;
  return text.slice(0, end);
}

/** 어절 수. 파이썬 len(text.split()). @param {string} text */
export function wordCount(text) {
  return splitWords(text).length;
}

/** @param {number[]} values */
export function mean(values) {
  return values.reduce((a, b) => a + b, 0) / values.length;
}

/** 모집단 표준편차 (파이썬 statistics.pstdev). @param {number[]} values */
export function pstdev(values) {
  const m = mean(values);
  return Math.sqrt(values.reduce((sum, v) => sum + (v - m) ** 2, 0) / values.length);
}

/** 부분 문자열 개수 (파이썬 str.count). @param {string} text @param {string} needle @param {number} [end] */
export function countIn(text, needle, end = text.length) {
  let count = 0;
  let from = 0;
  const limit = end;
  while (true) {
    const at = text.indexOf(needle, from);
    if (at < 0 || at + needle.length > limit) return count;
    count++;
    from = at + needle.length;
  }
}
