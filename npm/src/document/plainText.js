// @ts-check
/**
 * 산문에서 마크다운 표식을 걷는다. 인라인 코드는 백틱만 떼고 내용은 남긴다. 링크는 보이는 글자만. 강조 표식은 뗀다.
 * 줄바꿈은 남겨 줄 번호 계산에 쓴다. 파이썬 document/plainText.py 와 같다.
 * 인라인 코드가 있던 자리는 codeSpans 로 다시 찾는다. 백틱 안은 사용이 아니라 인용이다.
 */

const INLINE_CODE = /`([^`\n]*)`/g;
const LINK = /\[([^\]]*)\]\([^)]*\)/g;
const EMPHASIS = /(\*\*|__)(?=\S)(.+?)(?<=\S)\1/g;
// 파이썬의 \w 는 유니코드 글자라 한글을 포함한다. JS 는 \p{L}\p{N}_ 로 같은 뜻을 적는다.
const SINGLE_EMPHASIS = /(?<![\p{L}\p{N}_*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\p{L}\p{N}_*])/gu;
const SPACES = /[ \t]+/g;

/** @param {string} text */
export function plainText(text) {
  text = text.replace(INLINE_CODE, "$1");
  text = text.replace(LINK, "$1");
  text = text.replace(EMPHASIS, "$2");
  text = text.replace(SINGLE_EMPHASIS, "$1");
  return text.replace(SPACES, " ").trim();
}

/**
 * 원문의 인라인 코드 내용이 plain 안에서 차지하는 [시작, 끝]. 앞에서부터 차례로 찾고 못 찾으면 건너뛴다.
 * @param {string} raw
 * @param {string} plain
 * @returns {[number, number][]}
 */
export function codeSpans(raw, plain) {
  /** @type {[number, number][]} */
  const spans = [];
  let cursor = 0;
  for (const match of raw.matchAll(INLINE_CODE)) {
    const needle = match[1].replace(SPACES, " ");
    if (!needle) continue;
    const at = plain.indexOf(needle, cursor);
    if (at < 0) continue;
    spans.push([at, at + needle.length]);
    cursor = at + needle.length;
  }
  return spans;
}
