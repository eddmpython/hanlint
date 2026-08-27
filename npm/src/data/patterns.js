// @ts-check
/**
 * 문형. 빈칸이 있는 문장 틀. 파이썬 data/patterns.py 와 같다.
 * 본보기가 고친 사례 하나라면 문형은 그 사례를 다시 쓸 수 있는 틀이다.
 */
import { loadEntries } from "./load.js";

/**
 * @typedef {object} Pattern
 * @property {string} name
 * @property {string} form 빈칸이 있는 틀
 * @property {string} when 이 틀을 꺼내는 자리
 * @property {string} example 그 틀로 쓴 문장. hanlint 를 통과한다
 * @property {string} instead 같은 자리에 흔히 쓰는 문장. avoids 의 규칙에 잡힌다
 * @property {string[]} avoids
 * @property {string} source
 */

/** @type {Pattern[] | null} */
let cache = null;

/** @returns {Pattern[]} */
export function patterns() {
  if (!cache) {
    cache = [];
    const seen = new Set();
    for (const entry of loadEntries("patterns.json")) {
      const name = /** @type {string} */ (entry.name);
      if (seen.has(name)) throw new Error(`문형 이름이 겹친다: ${name}`);
      seen.add(name);
      cache.push({
        name,
        form: /** @type {string} */ (entry.form),
        when: /** @type {string} */ (entry.when),
        example: /** @type {string} */ (entry.example),
        instead: /** @type {string} */ (entry.instead),
        avoids: /** @type {string[]} */ (entry.avoids),
        source: /** @type {string} */ (entry.source),
      });
    }
  }
  return cache;
}

/** 그 규칙을 피하는 문형들. @param {string} rule */
export function patternsAvoiding(rule) {
  return patterns().filter((pattern) => pattern.avoids.includes(rule));
}
