// @ts-check
/**
 * 예시. 규칙마다 고치기 전과 고친 뒤의 짝. 파이썬 data/exemplars.py와 같다.
 *
 * 지적은 무엇이 틀렸는지 말하고 예시는 무엇이 맞는지 보인다. 자리표시자 규칙은 fixture와 같다.
 * `{em}`은 긴 줄표, `{dot}`은 마침표다.
 */
import { loadEntries } from "./load.js";

const EM_DASH = String.fromCharCode(0x2014);
const EN_DASH = String.fromCharCode(0x2013);
const ELLIPSIS_CHAR = String.fromCharCode(0x2026);
/** 한 줄 예시의 표시 폭 상한. 글자 수가 아니라 폭이다. 까닭은 파이썬 data/exemplars.py에 적었다. */
const ONE_LINE_LIMIT = 96;
/** 두 칸을 차지하는 글자. 한중일 W와 F다. 파이썬 unicodedata.east_asian_width와 같은 범위다. */
const WIDE = /[\u1100-\u115F\u2E80-\u303E\u3041-\u33FF\u3400-\u4DBF\u4E00-\u9FFF\uA000-\uA4CF\uAC00-\uD7A3\uF900-\uFAFF\uFE30-\uFE6F\uFF00-\uFF60\uFFE0-\uFFE6]/;

/**
 * @typedef {object} Exemplar
 * @property {string} rule
 * @property {string} before 그 규칙에 실제로 잡히는 글
 * @property {string} after 같은 뜻이면서 잡히지 않는 글
 * @property {string} moved 무엇이 달라졌는지 한 마디
 * @property {string[]} presets 비어 있으면 기본, 값이 있으면 그 프리셋의 문맥 예시
 */

/** @param {string} text */
export function expand(text) {
  return text.split("{em}").join(EM_DASH).split("{en}").join(EN_DASH).split("{dot}").join(".");
}

/** 터미널에서 차지하는 칸 수. 한중일 글자는 둘, 나머지는 하나다. @param {string} text */
export function displayWidth(text) {
  let width = 0;
  for (const ch of text) width += WIDE.test(ch) ? 2 : 1;
  return width;
}

/** 한 줄로 보일 때의 모양. 줄바꿈은 공백으로 바꾸고 폭이 넘치면 자른다. @param {string} text @param {number} [limit] */
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

/** @type {Exemplar[] | null} */
let allCache = null;
/** @type {Map<string, Exemplar> | null} */
let defaultCache = null;

/** 기본 예시와 문맥 예시를 모두 읽는다. @returns {Exemplar[]} */
export function allExemplars() {
  if (!allCache) {
    allCache = [];
    const defaults = new Set();
    /** @type {Map<string, Set<string>>} */
    const contexts = new Map();
    for (const entry of loadEntries("exemplars.json")) {
      const rule = /** @type {string} */ (entry.rule);
      const presets = /** @type {string[]} */ (entry.presets ?? []);
      if (!presets.length) {
        if (defaults.has(rule)) throw new Error(`기본 예시가 겹친다: ${rule}`);
        defaults.add(rule);
      } else {
        const used = contexts.get(rule) ?? new Set();
        const overlap = presets.filter((preset) => used.has(preset)).sort();
        if (overlap.length) throw new Error(`문맥 예시의 프리셋이 겹친다: ${rule} ${overlap.join(", ")}`);
        for (const preset of presets) used.add(preset);
        contexts.set(rule, used);
      }
      allCache.push({
        rule,
        before: expand(/** @type {string} */ (entry.before)),
        after: expand(/** @type {string} */ (entry.after)),
        moved: /** @type {string} */ (entry.moved),
        presets,
      });
    }
  }
  return allCache;
}

/** 규칙 이름 → 예시. @returns {Map<string, Exemplar>} */
export function exemplars() {
  if (!defaultCache) {
    defaultCache = new Map(
      allExemplars().filter((exemplar) => !exemplar.presets.length).map((exemplar) => [exemplar.rule, exemplar]),
    );
  }
  return defaultCache;
}

/** 설정의 `[[exemplars]]`를 검증한다. @param {unknown} entries @param {string[]} presetNames @returns {Exemplar[]} */
export function projectExemplars(entries, presetNames) {
  if (!Array.isArray(entries)) throw new Error("exemplars는 [[exemplars]] 배열이어야 한다");
  const allowedKeys = new Set(["rule", "before", "after", "moved", "presets"]);
  const knownRules = new Set(exemplars().keys());
  const knownPresets = new Set(presetNames);
  const defaults = new Set();
  /** @type {Map<string, Set<string>>} */
  const contexts = new Map();
  return entries.map((raw, offset) => {
    const index = offset + 1;
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error(`exemplars ${index}번째 항목은 표여야 한다`);
    const entry = /** @type {Record<string, unknown>} */ (raw);
    const unknown = Object.keys(entry).filter((key) => !allowedKeys.has(key)).sort();
    if (unknown.length) throw new Error(`exemplars ${index}번째 항목의 모르는 키: ${unknown.join(", ")}`);
    /** @type {Record<string, string>} */
    const values = {};
    for (const key of ["rule", "before", "after", "moved"]) {
      const value = entry[key];
      if (typeof value !== "string" || !value.trim()) {
        throw new Error(`exemplars ${index}번째 항목의 ${key} 값은 비지 않은 문자열이어야 한다`);
      }
      values[key] = value;
    }
    const rule = values.rule;
    if (!knownRules.has(rule)) throw new Error(`exemplars ${index}번째 항목의 모르는 규칙: ${rule}`);
    const rawPresets = entry.presets ?? [];
    if (!Array.isArray(rawPresets) || !rawPresets.every((item) => typeof item === "string")) {
      throw new Error(`exemplars ${index}번째 항목의 presets는 문자열 배열이어야 한다`);
    }
    const presets = /** @type {string[]} */ (rawPresets);
    const unknownPresets = [...new Set(presets.filter((preset) => !knownPresets.has(preset)))].sort();
    if (unknownPresets.length) {
      throw new Error(`exemplars ${index}번째 항목의 모르는 프리셋: ${unknownPresets.join(", ")}`);
    }
    if (new Set(presets).size !== presets.length) throw new Error(`프로젝트 예시의 프리셋이 겹친다: ${rule}`);
    if (!presets.length) {
      if (defaults.has(rule)) throw new Error(`프로젝트 기본 예시가 겹친다: ${rule}`);
      defaults.add(rule);
    } else {
      const used = contexts.get(rule) ?? new Set();
      const overlap = presets.filter((preset) => used.has(preset)).sort();
      if (overlap.length) throw new Error(`프로젝트 예시의 프리셋이 겹친다: ${rule} ${overlap.join(", ")}`);
      for (const preset of presets) used.add(preset);
      contexts.set(rule, used);
    }
    return { rule, before: expand(values.before), after: expand(values.after), moved: values.moved, presets };
  });
}

/** @param {string} rule @param {string | null | undefined} [preset] @param {Exemplar[]} [customExemplars] @returns {Exemplar | undefined} */
export function exemplarFor(rule, preset = null, customExemplars = []) {
  if (preset) {
    const contextual = customExemplars.find((exemplar) => exemplar.rule === rule && exemplar.presets.includes(preset));
    if (contextual) return contextual;
    const builtInContextual = allExemplars().find((exemplar) => exemplar.rule === rule && exemplar.presets.includes(preset));
    if (builtInContextual) return builtInContextual;
  }
  const customDefault = customExemplars.find((exemplar) => exemplar.rule === rule && !exemplar.presets.length);
  if (customDefault) return customDefault;
  return exemplars().get(rule);
}

/** 전과 후를 한 줄씩. @param {Exemplar} exemplar @returns {[string, string]} */
export function twoLines(exemplar) {
  return [shorten(exemplar.before), shorten(exemplar.after)];
}

/** 어느 한쪽이라도 잘렸나. @param {Exemplar} exemplar */
export function shortened(exemplar) {
  return isShortened(exemplar.before) || isShortened(exemplar.after);
}
