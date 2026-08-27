// @ts-check
/**
 * 파이썬 re 와 같은 뜻으로 쓰는 얇은 껍질. search 는 첫 자리, at 은 문자열 첫머리에서만, all 은 전부.
 * 정규식 문법은 데이터 파일과 규칙에서 파이썬과 같은 부분집합만 쓴다 (lookbehind 포함, 이름 그룹 없음).
 */

const BACKSLASH = String.fromCharCode(92);
const SPECIALS = new RegExp(`[.*+?^\${}()|[${BACKSLASH}]${BACKSLASH}${BACKSLASH}/-]`, "g");

/**
 * @typedef {object} Pattern
 * @property {string} source
 * @property {(text: string) => RegExpExecArray | null} search 파이썬 re.search
 * @property {(text: string) => RegExpExecArray | null} at 파이썬 re.match (첫머리에서만)
 * @property {(text: string) => RegExpExecArray[]} all 파이썬 re.finditer
 */

/**
 * @param {string} source
 * @param {string} [flags] u 같은 추가 플래그
 * @returns {Pattern}
 */
export function compile(source, flags = "") {
  const once = new RegExp(source, flags);
  const sticky = new RegExp(source, `${flags}y`);
  const every = new RegExp(source, `${flags}g`);
  return {
    source,
    search(text) {
      once.lastIndex = 0;
      return once.exec(text);
    },
    at(text) {
      sticky.lastIndex = 0;
      return sticky.exec(text);
    },
    all(text) {
      every.lastIndex = 0;
      return [...text.matchAll(every)];
    },
  };
}

/** 정규식 특수문자를 이스케이프한다 (파이썬 re.escape 의 쓰임새). @param {string} text */
export function escape(text) {
  return text.replace(SPECIALS, (c) => BACKSLASH + c);
}
