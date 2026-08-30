// @ts-check
/** 글쓴이가 승인한 원문 완전 일치 고침. 파이썬 data/patches.py와 같은 선택 계약이다. */
import { exemplars, expand } from "./exemplars.js";

export const READER_KINDS = ["recent", "known", "new", "none"];

/**
 * @typedef {object} Patch
 * @property {string} rule
 * @property {string} before
 * @property {string} after
 * @property {string} moved
 * @property {string} cue
 * @property {string} reader
 * @property {string[]} presets
 * @property {string} sentence 마크다운 표식을 걷은 선택용 원문
 * @property {string} sourceText 마크다운 표식을 보존한 선택용 원문
 */

/** 줄과 연속 공백 차이는 선택 조건으로 쓰지 않는다. @param {string} text */
export function flatCue(text) {
  return text.split(/\s+/).filter(Boolean).join(" ");
}

/** 승인 원문은 유니코드 조합과 줄, 연속 공백만 눕혀 비교한다. @param {string} text */
export function flatSentence(text) {
  return text.normalize("NFC").split(/\s+/).filter(Boolean).join(" ");
}

/** 설정의 `[[patches]]`를 검증한다. @param {unknown} entries @param {string[]} presetNames @returns {Patch[]} */
export function projectPatches(entries, presetNames) {
  if (!Array.isArray(entries)) throw new Error("patches 는 [[patches]] 배열이다");
  const allowedKeys = new Set(["rule", "before", "after", "moved", "sourceText", "sentence", "cue", "reader", "presets"]);
  const knownRules = new Set(exemplars().keys());
  const knownPresets = new Set(presetNames);
  const selectors = new Set();
  return entries.map((raw, offset) => {
    const index = offset + 1;
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error(`patches ${index}번째 항목은 표다`);
    const entry = /** @type {Record<string, unknown>} */ (raw);
    const unknown = Object.keys(entry).filter((key) => !allowedKeys.has(key)).sort();
    if (unknown.length) throw new Error(`patches ${index}번째 항목의 모르는 키: ${unknown.join(", ")}`);
    /** @type {Record<string, string>} */
    const values = {};
    for (const key of ["rule", "before", "after", "moved", "cue", "reader"]) {
      const value = entry[key];
      if (typeof value !== "string" || !value.trim()) {
        throw new Error(`patches ${index}번째 항목의 ${key} 는 비지 않은 문자열이다`);
      }
      values[key] = value;
    }
    const rule = values.rule;
    if (!knownRules.has(rule)) throw new Error(`patches ${index}번째 항목의 모르는 규칙: ${rule}`);
    const reader = values.reader;
    if (!READER_KINDS.includes(reader)) {
      throw new Error(`patches ${index}번째 항목의 reader 는 ${READER_KINDS.join(", ")} 가운데 하나다: ${reader}`);
    }
    const rawPresets = entry.presets;
    if (!Array.isArray(rawPresets) || !rawPresets.length || !rawPresets.every((item) => typeof item === "string")) {
      throw new Error(`patches ${index}번째 항목의 presets 는 비지 않은 문자열 배열이다`);
    }
    const presets = /** @type {string[]} */ (rawPresets);
    const unknownPresets = [...new Set(presets.filter((preset) => !knownPresets.has(preset)))].sort();
    if (unknownPresets.length) {
      throw new Error(`patches ${index}번째 항목의 모르는 프리셋: ${unknownPresets.join(", ")}`);
    }
    if (new Set(presets).size !== presets.length) throw new Error(`패치의 프리셋이 겹친다: ${rule}`);
    const cue = flatCue(values.cue);
    const before = expand(values.before);
    const after = expand(values.after);
    const rawSentence = entry.sentence ?? before;
    if (typeof rawSentence !== "string" || !rawSentence.trim()) {
      throw new Error(`patches ${index}번째 항목의 sentence 는 비지 않은 문자열이다`);
    }
    const sentence = flatSentence(rawSentence);
    const rawSourceText = entry.sourceText ?? before;
    if (typeof rawSourceText !== "string" || !rawSourceText.trim()) {
      throw new Error(`patches ${index}번째 항목의 sourceText 는 비지 않은 문자열이다`);
    }
    const sourceText = flatSentence(rawSourceText);
    for (const preset of presets) {
      const selector = JSON.stringify([rule, preset, sourceText, sentence, cue, reader]);
      if (selectors.has(selector)) throw new Error(`패치 선택 조건이 겹친다: ${rule} ${preset} ${cue} ${reader}`);
      selectors.add(selector);
    }
    return {
      rule,
      before,
      after,
      moved: values.moved,
      cue,
      reader,
      presets,
      sentence,
      sourceText,
    };
  });
}

/**
 * 원문을 포함한 모든 조건이 맞는 패치가 하나일 때만 돌려준다.
 * @param {string} rule
 * @param {string | null | undefined} preset
 * @param {string} sourceText
 * @param {string} sentence
 * @param {string} cue
 * @param {string | null | undefined} reader
 * @param {Patch[]} patches
 */
export function patchFor(rule, preset, sourceText, sentence, cue, reader, patches) {
  if (!preset || !reader || !READER_KINDS.includes(reader)) return undefined;
  const wantedCue = flatCue(cue);
  const wantedSourceText = flatSentence(sourceText);
  const wantedSentence = flatSentence(sentence);
  const matches = patches.filter(
    (patch) =>
      patch.rule === rule &&
      patch.presets.includes(preset) &&
      patch.sourceText === wantedSourceText &&
      patch.sentence === wantedSentence &&
      patch.cue === wantedCue &&
      patch.reader === reader,
  );
  return matches.length === 1 ? matches[0] : undefined;
}
