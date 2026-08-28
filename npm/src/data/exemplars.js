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
/** 한 줄 본보기의 표시 폭 상한. 글자 수가 아니라 폭이다. 뜻은 파이썬 data/exemplars.py 가 소유한다. */
const ONE_LINE_LIMIT = 96;
/** 칸을 둘 먹는 글자. 한중일 W 와 F 다. 파이썬 unicodedata.east_asian_width 와 같은 범위를 든다. */
const WIDE = /[\u1100-\u115F\u2E80-\u303E\u3041-\u33FF\u3400-\u4DBF\u4E00-\u9FFF\uA000-\uA4CF\uAC00-\uD7A3\uF900-\uFAFF\uFE30-\uFE6F\uFF00-\uFF60\uFFE0-\uFFE6]/;

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

/** 터미널이 먹는 칸 수. 한중일 글자는 둘, 나머지는 하나다. @param {string} text */
export function displayWidth(text) {
  let width = 0;
  for (const ch of text) width += WIDE.test(ch) ? 2 : 1;
  return width;
}

/** 한 줄로 보일 때의 꼴. 줄바꿈은 공백으로 눕히고 폭이 넘치면 자른다. @param {string} text @param {number} [limit] */
export function shorten(text, limit = ONE_LINE_LIMIT) {
  const flat = text.split(/\s+/).filter(Boolean).join(" ");
  if (displayWidth(flat) <= limit) return flat;
  let kept = "";
  let used = 0;
  for (const ch of flat) {
    const step = WIDE.test(ch) ? 2 : 1;
    if (used + step > limit - 1) break;
    kept += ch;
    used += step;
  }
  return kept + ELLIPSIS_CHAR;
}

/** @param {string} text */
export function isShortened(text) {
  return displayWidth(text.split(/\s+/).filter(Boolean).join(" ")) > ONE_LINE_LIMIT;
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

/** 전과 후를 제 줄씩. @param {Exemplar} exemplar @returns {[string, string]} */
export function twoLines(exemplar) {
  return [shorten(exemplar.before), shorten(exemplar.after)];
}

/** 어느 한쪽이라도 잘렸나. @param {Exemplar} exemplar */
export function shortened(exemplar) {
  return isShortened(exemplar.before) || isShortened(exemplar.after);
}
