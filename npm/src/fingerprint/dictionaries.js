// @ts-check
/** 사전 넷을 한 번 컴파일하고 문장에서 맞는 자리를 찾는다. 설정의 dictionary 항목을 더한다. */
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
};
const GROUP_REF = /\$(\d)/g;
const FINALS = { ㄴ: 4, ㄹ: 8 };
// {조사} 자리표시자. 낱말 뒤에 조사가 붙었거나 낱말이 끝나는 자리. 파이썬 dictionaries.py 와 같은 글자다.
const JOSA_TAIL = "(?=(?:에서는|으로는|에서|에게|까지|부터|보다|처럼|으로|이나|은|는|이|가|을|를|의|에|로|와|과|도|만)?(?![가-힣]))";
const PLACEHOLDER = /\{(ㄴ|ㄹ|조사)\}/g;

/** 받침으로 끝나는 음절 399개의 문자 부류. @param {"ㄴ" | "ㄹ"} final */
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
 */

/** @param {string} dictionary @param {Record<string, unknown> | string} raw @returns {Entry} */
export function entryFrom(dictionary, raw) {
  const data = typeof raw === "string" ? { pattern: raw } : raw;
  return {
    dictionary,
    pattern: compile(expandClasses(/** @type {string} */ (data.pattern))),
    why: /** @type {string} */ (data.why ?? "설정에서 더한 항목"),
    source: /** @type {string} */ (data.source ?? "설정"),
    fix: /** @type {string | null} */ (data.fix ?? null),
  };
}

/** @type {Entry[] | null} */
let builtinCache = null;
export function builtinEntries() {
  if (!builtinCache) {
    builtinCache = [];
    for (const [dictionary, name] of Object.entries(DICTIONARY_FILES)) {
      for (const raw of loadEntries(name)) builtinCache.push(entryFrom(dictionary, raw));
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
      throw new Error(`모르는 사전: ${dictionary}. ${Object.keys(DICTIONARY_FILES).join(", ")} 가운데 하나다`);
    }
    for (const raw of items) extra.push(entryFrom(dictionary, /** @type {Record<string, unknown> | string} */ (raw)));
  }
  return [...builtinEntries(), ...extra];
}

/** @param {RegExpExecArray} match @param {string} fix */
export function applyFix(match, fix) {
  return fix.replace(GROUP_REF, (_, n) => match[Number(n)] ?? "");
}

/** @param {string} text @param {Entry[]} entries @returns {DictionaryMatch[]} */
export function matchesIn(text, entries) {
  /** @type {DictionaryMatch[]} */
  const found = [];
  for (const entry of entries) {
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
      });
    }
  }
  found.sort((a, b) => a.start - b.start);
  return found;
}
