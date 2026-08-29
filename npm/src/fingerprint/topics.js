// @ts-check
/** 화제어 집합. 조사를 뗀 명사 어절의 근사. 파이썬 fingerprint/topics.py 와 같다. */
import { stripJosa, tailOf, words } from "../analysis/tokenize.js";
import { loadLines } from "../data/load.js";

const WORD = /^[가-힣A-Za-z][가-힣A-Za-z0-9]*$/;

/** @type {Set<string> | null} */
let stopwordCache = null;
function stopwords() {
  if (!stopwordCache) stopwordCache = new Set(loadLines("stopwords.txt"));
  return stopwordCache;
}

/** @param {string} text @returns {Set<string>} */
export function topicsOf(text) {
  const found = new Set();
  for (const word of words(text)) {
    const core = stripJosa(word.core);
    if (!WORD.test(core) || stopwords().has(core)) continue;
    // 한 글자는 조사가 붙어 있던 것만 명사로 본다 (표를, 값이, 열은). 홀로 선 한 글자는 잡음이다.
    if (core.length < 2 && core === word.core) continue;
    if (tailOf(core, "verbTails.txt")) continue;
    found.add(core.toLowerCase());
  }
  return found;
}

/** 자카드 유사도. 둘 다 비어 있으면 0. @param {Set<string>} a @param {Set<string>} b */
export function overlap(a, b) {
  if (!a.size || !b.size) return 0;
  let shared = 0;
  for (const item of a) if (b.has(item)) shared += 1;
  return shared / (a.size + b.size - shared);
}

/** @param {Iterable<Set<string>>} sets */
export function unionOf(sets) {
  const result = new Set();
  for (const set of sets) for (const item of set) result.add(item);
  return result;
}
