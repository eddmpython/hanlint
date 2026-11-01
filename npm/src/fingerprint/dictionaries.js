// @ts-check
/** 사전들을 한 번 컴파일하고 문장에서 맞는 부분을 찾는다. 설정의 dictionary 항목을 더한다. */
import { loadEntries } from "../data/load.js";
import { compile } from "../regex.js";

export const DICTIONARY_FILES = {
  cliches: "cliches.toml",
  translationese: "translationese.toml",
  redundantPair: "redundantPair.toml",
  japaneseLoan: "japaneseLoan.toml",
  spelling: "spelling.toml",
  spacing: "spacing.toml",
  confusable: "confusable.toml",
  easyWords: "easyWords.toml",
  screenSentence: "screenSentence.toml",
  screenNarration: "screenNarration.toml",
  screenTone: "screenTone.toml",
  screenWord: "screenWord.toml",
  calqueFrame: "calqueFrame.toml",
};
const GROUP_REF = /\$(\d)/g;
const FINALS = { ㄴ: 4, ㄹ: 8 };
// {조사} 자리표시자. 단어 뒤에 조사가 붙었거나 단어가 끝나는 곳. 파이썬 dictionaries.py와 같은 글자다.
const JOSA_TAIL = "(?=(?:에서는|으로는|에서|에게|까지|부터|보다|처럼|으로|이나|은|는|이|가|을|를|의|에|로|와|과|도|만)?(?![가-힣]))";
const PLACEHOLDER = /\{(ㄴ|ㄹ|조사)\}/g;

/** 받침으로 끝나는 음절 399개의 글자 집합. @param {"ㄴ" | "ㄹ"} final */
function syllableClass(final) {
  let chars = "";
  for (let initial = 0; initial < 19; initial++) {
    for (let vowel = 0; vowel < 21; vowel++) chars += String.fromCharCode(0xac00 + (initial * 21 + vowel) * 28 + FINALS[final]);
  }
  return `[${chars}]`;
}

/** @param {string} pattern */
export function expandClasses(pattern) {
  return pattern.replace(PLACEHOLDER, (_, name) => (name === "조사" ? JOSA_TAIL : syllableClass(name)));
}

/**
 * @typedef {object} Entry
 * @property {string} dictionary
 * @property {import("../regex.js").Pattern} pattern
 * @property {string} why
 * @property {string} source
 * @property {string | null} fix
 * @property {{ pattern: import("../regex.js").Pattern, into: string }[]} to 문장 전체를 다시 쓰는 규칙. 앞의 것부터 시도한다
 * @property {string} raw pattern의 원문. 내장 항목만 갖고 설정 항목은 빈 글자라 관용으로 접히지 않는다
 * @property {import("../regex.js").Pattern | null} unless 문장 전체에서 이것이 맞으면 그 문장에서는 항목이 맞지 않는다. 파이썬 Entry.unless와 같다
 */

/**
 * @typedef {object} DictionaryMatch
 * @property {string} dictionary
 * @property {string} text
 * @property {number} start
 * @property {number} end
 * @property {string} why
 * @property {string} source
 * @property {string | null} fix
 * @property {string | null} rewrite 항목의 to 규칙으로 문장 전체를 다시 쓴 제안. 없거나 안 맞으면 null
 * @property {string} pattern 맞은 항목의 pattern 원문. 용례 빈도표의 키다
 */

/** @param {string} dictionary @param {Record<string, unknown> | string} raw @param {boolean} [builtin] @returns {Entry} */
export function entryFrom(dictionary, raw, builtin = false) {
  const data = typeof raw === "string" ? { pattern: raw } : raw;
  return {
    dictionary,
    pattern: compile(expandClasses(/** @type {string} */ (data.pattern))),
    why: /** @type {string} */ (data.why ?? "설정에서 더한 항목"),
    source: /** @type {string} */ (data.source ?? "설정"),
    fix: /** @type {string | null} */ (data.fix ?? null),
    to: (/** @type {[string, string][]} */ (data.to ?? [])).map(([source, into]) => ({ pattern: compile(expandClasses(source)), into })),
    raw: builtin ? /** @type {string} */ (data.pattern) : "",
    unless: data.unless ? compile(expandClasses(/** @type {string} */ (data.unless))) : null,
  };
}

/** @type {Entry[] | null} */
let builtinCache = null;
export function builtinEntries() {
  if (!builtinCache) {
    builtinCache = [];
    for (const [dictionary, name] of Object.entries(DICTIONARY_FILES)) {
      for (const raw of loadEntries(name)) builtinCache.push(entryFrom(dictionary, raw, true));
    }
  }
  return builtinCache;
}

/** @param {import("../config/settings.js").Config} config @returns {Entry[]} */
export function entriesFor(config) {
  /** @type {Entry[]} */
  const extra = [];
  for (const [dictionary, items] of Object.entries(config.dictionary)) {
    if (!(dictionary in DICTIONARY_FILES)) {
      throw new Error(`모르는 사전: ${dictionary}. 쓸 수 있는 이름: ${Object.keys(DICTIONARY_FILES).join(", ")}`);
    }
    for (const raw of items) extra.push(entryFrom(dictionary, /** @type {Record<string, unknown> | string} */ (raw)));
  }
  return [...builtinEntries(), ...extra];
}

/** @param {RegExpExecArray} match @param {string} fix */
export function applyFix(match, fix) {
  return fix.replace(GROUP_REF, (_, n) => match[Number(n)] ?? "");
}

/**
 * to 규칙으로 문장을 다시 쓴다. 빈 그룹이 남긴 겹 공백은 하나로 줄이고 양끝을 다듬는다. 원문과 같으면 null.
 * 뜻은 파이썬 fingerprint/dictionaries.py의 rewriteBy가 정한다.
 * @param {string} text @param {Entry["to"]} rules
 */
export function rewriteBy(text, rules) {
  for (const { pattern, into } of rules) {
    const match = pattern.search(text);
    if (!match) continue;
    const rewritten = applyFix(match, into).split(/\s+/).filter(Boolean).join(" ");
    return rewritten && rewritten !== text ? rewritten : null;
  }
  return null;
}

/** @param {string} text @param {Entry[]} entries @returns {DictionaryMatch[]} */
export function matchesIn(text, entries) {
  /** @type {DictionaryMatch[]} */
  const found = [];
  for (const entry of entries) {
    if (entry.unless && entry.unless.search(text)) continue;
    for (const match of entry.pattern.all(text)) {
      const start = /** @type {number} */ (match.index);
      found.push({
        dictionary: entry.dictionary,
        text: match[0],
        start,
        end: start + match[0].length,
        why: entry.why,
        source: entry.source,
        fix: entry.fix ? applyFix(match, entry.fix) : null,
        rewrite: entry.to.length ? rewriteBy(text, entry.to) : null,
        pattern: entry.raw,
      });
    }
  }
  found.sort((a, b) => a.start - b.start);
  return found;
}
