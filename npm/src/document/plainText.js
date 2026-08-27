// @ts-check
/**
 * 산문에서 마크다운 표식을 걷는다. 인라인 코드는 백틱만 떼고 내용은 남긴다. 링크는 보이는 글자만. 강조 표식은 뗀다.
 * 줄바꿈은 남겨 줄 번호 계산에 쓴다. 파이썬 document/plainText.py 와 같다.
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
