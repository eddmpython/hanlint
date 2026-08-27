// @ts-check
/** 종결 부호 뒤 공백에서 문장을 나눈다. 파이썬 analysis/surface/splitSentences.py 와 같다. */

const TERMINAL = /[.?!]+\s+(?=\S)/g;
const ABBREVIATION = /(?:^|[^A-Za-z])[A-Za-z]$/;

/**
 * @typedef {object} Sentence
 * @property {string} text
 * @property {number} start 분석에 넣은 문자열 안의 시작 오프셋
 * @property {number} end
 */

/** @param {string} text @returns {Sentence[]} */
export function splitSentences(text) {
  /** @type {Sentence[]} */
  const sentences = [];
  let start = 0;
  for (const match of text.matchAll(TERMINAL)) {
    const index = /** @type {number} */ (match.index);
    const before = text.slice(0, index);
    if (ABBREVIATION.test(before)) continue;
    const end = index + match[0].trimEnd().length;
    const segment = text.slice(start, end);
    const piece = segment.trim();
    if (piece) sentences.push({ text: piece, start: start + (segment.length - segment.trimStart().length), end });
    start = index + match[0].length;
  }
  const rest = text.slice(start);
  const tail = rest.trim();
  if (tail) {
    const lead = rest.length - rest.trimStart().length;
    sentences.push({ text: tail, start: start + lead, end: start + lead + tail.length });
  }
  return sentences;
}
