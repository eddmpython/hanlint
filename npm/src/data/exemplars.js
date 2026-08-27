// @ts-check
/**
 * 본보기. 규칙마다 고치기 전과 후의 짝. 파이썬 data/exemplars.py 와 같다.
 *
 * 지적은 무엇이 틀렸는지 말하고 본보기는 무엇이 맞는지 보인다. 자리표시자 규약은 fixture 와 같다.
 * `{em}` 은 긴 줄표, `{dot}` 은 마침표다.
 */
import { loadEntries } from "./load.js";

const EM_DASH = String.fromCharCode(0x2014);
const EN_DASH = String.fromCharCode(0x2013);
const ELLIPSIS_CHAR = String.fromCharCode(0x2026);
/** 전과 후를 잇는 표지. 긴 줄표를 쓸 수 없으므로 화살표다. */
const ARROW = " -> ";
/** 한 줄 본보기의 한쪽 글자 상한. */
const ONE_LINE_LIMIT = 46;

/**
 * @typedef {object} Exemplar
 * @property {string} rule
 * @property {string} before 그 규칙에 실제로 잡히는 글
 * @property {string} after 같은 뜻이면서 잡히지 않는 글
 * @property {string} moved 무엇이 달라졌는지 한 마디
 */

/** @param {string} text */
export function expand(text) {
  return text.split("{em}").join(EM_DASH).split("{en}").join(EN_DASH).split("{dot}").join(".");
}

/** 한 줄로 보일 때의 꼴. 줄바꿈은 공백으로 눕히고 길면 자른다. @param {string} text @param {number} [limit] */
export function shorten(text, limit = ONE_LINE_LIMIT) {
  const flat = text.split(/\s+/).filter(Boolean).join(" ");
  return flat.length <= limit ? flat : flat.slice(0, limit - 1) + ELLIPSIS_CHAR;
}

/** @type {Map<string, Exemplar> | null} */
let cache = null;

/** 규칙 이름 → 본보기. @returns {Map<string, Exemplar>} */
export function exemplars() {
  if (!cache) {
    cache = new Map();
    for (const entry of loadEntries("exemplars.json")) {
      const rule = /** @type {string} */ (entry.rule);
      if (cache.has(rule)) throw new Error(`본보기가 겹친다: ${rule}. 규칙 하나에 하나다`);
      cache.set(rule, {
        rule,
        before: expand(/** @type {string} */ (entry.before)),
        after: expand(/** @type {string} */ (entry.after)),
        moved: /** @type {string} */ (entry.moved),
      });
    }
  }
  return cache;
}

/** @param {string} rule @returns {Exemplar | undefined} */
export function exemplarFor(rule) {
  return exemplars().get(rule);
}

/** 한 줄로 줄인 짝. @param {Exemplar} exemplar */
export function oneLine(exemplar) {
  return shorten(exemplar.before) + ARROW + shorten(exemplar.after);
}
