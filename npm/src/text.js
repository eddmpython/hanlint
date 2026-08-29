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

/**
 * 파이썬 round(value, digits). 정확한 이진 값을 십진으로 풀어 반올림하고 정확히 절반이면 짝수로 간다.
 * Math.round 는 절반을 위로 올려 13/16 을 0.813 으로 만들고 파이썬은 0.812 다. 두 판의 글자가 같으려면 파이썬 쪽이다.
 * toFixed(100) 은 1e21 아래의 수를 정확한 십진 전개로 준다. 지문의 비율과 평균이 사는 범위다.
 * @param {number} value
 * @param {number} digits
 */
export function roundHalfEven(value, digits) {
  if (!Number.isFinite(value) || Math.abs(value) >= 1e21) return value;
  const sign = value < 0 ? -1 : 1;
  const [whole, fraction] = Math.abs(value).toFixed(100).split(".");
  const rest = fraction.slice(digits);
  let units = BigInt(whole + fraction.slice(0, digits));
  const next = rest.charCodeAt(0) - 48;
  const halfway = next === 5 && /^0*$/.test(rest.slice(1));
  if (next > 5 || (next === 5 && !halfway) || (halfway && units % 2n === 1n)) units += 1n;
  return sign * (Number(units) / 10 ** digits);
}
