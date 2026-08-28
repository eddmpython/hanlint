// @ts-check
/** 파이썬 `analysis/grammar/ending.py`와 `predicate.py`의 투영. 종결 서술어를 풀고 세 문체로 짠다. */
import { loadLines } from "../../data/load.js";
import * as hangul from "./hangul.js";

export const VERB = "동사";
export const ADJECTIVE = "형용사";
export const COPULA = "계사";
export const PRESENT = "현재";
export const PAST = "과거";
export const FUTURE = "미래";
export const DECLARATIVE = "평서";
export const QUESTION = "의문";
export const KKA_QUESTION = "까의문";
export const IMPERATIVE = "명령";
export const PROPOSITIVE = "청유";
export const HAPNIDA = "합니다";
export const HANDA = "한다";
export const HAEYO = "해요";
export const REGISTERS = [HAPNIDA, HANDA, HAEYO];

const HAE_IRREGULAR = new Map([
  ["그렇", "그래"],
  ["이렇", "이래"],
  ["저렇", "저래"],
  ["어떻", "어때"],
]);
const AUX_LINKS = ["지는", "지도", "지만", "지"];

let adjectiveCache = null;
let rieulCache = null;
let iVerbCache = null;
let irregularCache = null;

function adjectiveStems() {
  if (!adjectiveCache) adjectiveCache = new Set(loadLines("adjectiveStems.txt"));
  return adjectiveCache;
}

function rieulStems() {
  if (!rieulCache) rieulCache = new Set(loadLines("rieulStems.txt"));
  return rieulCache;
}

function iVerbStems() {
  if (!iVerbCache) iVerbCache = new Set(loadLines("iVerbStems.txt"));
  return iVerbCache;
}

function irregularStems() {
  if (!irregularCache) {
    irregularCache = loadLines("irregularStems.txt")
      .map((line) => line.split("\t"))
      .sort((a, b) => b[0].length - a[0].length);
  }
  return irregularCache;
}

/** @param {string} stem */
export function isAdjective(stem) {
  return adjectiveStems().has(stem);
}

/** @param {string} stem */
function irregularClass(stem) {
  for (const [known, kind] of irregularStems()) {
    if (stem === known || stem.endsWith(known)) return kind;
  }
  return null;
}

/** @param {string} base */
function restoreRieul(base) {
  const last = hangul.lastSyllable(base);
  if (last === null || hangul.finalOf(last) !== hangul.NONE) return base;
  const candidate = base.slice(0, -1) + hangul.withFinal(last, hangul.RIEUL);
  return rieulStems().has(candidate) ? candidate : base;
}

/** @param {string} base */
function stripEu(base) {
  if (base.length >= 2 && base.endsWith("으") && hangul.isSyllable(base.at(-2)) && hangul.finalOf(base.at(-2)) !== hangul.NONE) {
    return base.slice(0, -1);
  }
  return base;
}

/** @param {string} base */
function tenseOf(base) {
  const last = hangul.lastSyllable(base);
  if (base.endsWith("겠")) return FUTURE;
  if (last !== null && last !== "있" && hangul.finalOf(last) === hangul.SSANGSIOT) return PAST;
  return PRESENT;
}

/** @param {string} base @param {string | null} previous */
function kindOf(base, previous) {
  if (base === "않" && previous) {
    for (const link of AUX_LINKS) {
      if (previous.endsWith(link) && previous.length > link.length) {
        return isAdjective(previous.slice(0, -link.length)) ? ADJECTIVE : VERB;
      }
    }
  }
  return isAdjective(base) ? ADJECTIVE : VERB;
}

/**
 * @typedef {object} Predicate
 * @property {string} base
 * @property {string} kind
 * @property {string} tense
 * @property {string} mood
 * @property {boolean} explicitCopula
 */

/** @param {string} base @param {string} kind @param {string} [tense] @param {string} [mood] @param {boolean} [explicitCopula] @returns {Predicate} */
function predicate(base, kind, tense = PRESENT, mood = DECLARATIVE, explicitCopula = false) {
  return { base, kind, tense, mood, explicitCopula };
}

/** @param {string} base @param {string | null} previous @param {string} mood */
function classifyPredicate(base, previous, mood) {
  if (!base) return null;
  const tense = tenseOf(base);
  const kind = tense !== PRESENT ? VERB : kindOf(base, previous);
  return predicate(base, kind, tense, mood);
}

/** @param {string} word @param {number} offset @param {number} final */
function endsWithFinal(word, offset, final) {
  if (word.length < offset) return false;
  const ch = word.at(-offset);
  return hangul.isSyllable(ch) && hangul.finalOf(ch) === final;
}

/** @param {string} word @param {number} offset */
function stemBefore(word, offset) {
  const ch = word.at(-offset);
  return word.slice(0, -offset) + hangul.withFinal(ch, hangul.NONE);
}

/** @param {string} noun @param {string} mood */
function copulaOrIVerb(noun, mood) {
  const stem = noun + "이";
  return iVerbStems().has(stem) ? predicate(stem, VERB, PRESENT, mood) : predicate(noun, COPULA, PRESENT, mood);
}

/** 문장 끝 한글 어절 하나를 푼다. @param {string} word @param {string | null} [previous] @returns {Predicate | null} */
export function parsePredicate(word, previous = null) {
  if (!word || !hangul.isSyllable(word.at(-1))) return null;
  if ((word === "다" || word === "입니다") && previous) return predicate("", COPULA);
  if (word === "아닙니다" || word === "아니다") return predicate("아니", ADJECTIVE);
  if (word.endsWith("입니다") && word.length > 3) return copulaOrIVerb(word.slice(0, -3), DECLARATIVE);
  if (word.endsWith("입니까") && word.length > 3) return copulaOrIVerb(word.slice(0, -3), QUESTION);
  if (word.endsWith("습니다")) return classifyPredicate(word.slice(0, -3), previous, DECLARATIVE);
  if (word.endsWith("습니까")) return classifyPredicate(word.slice(0, -3), previous, QUESTION);
  if (word.endsWith("니다") && endsWithFinal(word, 3, hangul.BIEUP)) {
    return classifyPredicate(restoreRieul(stemBefore(word, 3)), previous, DECLARATIVE);
  }
  if (word.endsWith("니까") && endsWithFinal(word, 3, hangul.BIEUP)) {
    return classifyPredicate(restoreRieul(stemBefore(word, 3)), previous, QUESTION);
  }
  if (word.endsWith("까요") && word.length > 2) return predicate(word.slice(0, -1), VERB, PRESENT, KKA_QUESTION);
  if (word.endsWith("십시오") && word.length > 3) {
    return predicate(restoreRieul(stripEu(word.slice(0, -3))), VERB, PRESENT, IMPERATIVE);
  }
  if (word.endsWith("세요") && word.length > 2) {
    return predicate(restoreRieul(stripEu(word.slice(0, -2))), VERB, PRESENT, IMPERATIVE);
  }
  if (word.endsWith("읍시다")) return predicate(word.slice(0, -3), VERB, PRESENT, PROPOSITIVE);
  if (word.endsWith("시다") && endsWithFinal(word, 3, hangul.BIEUP)) {
    return predicate(restoreRieul(stemBefore(word, 3)), VERB, PRESENT, PROPOSITIVE);
  }
  if (word.endsWith("는다") && word.length > 2) return predicate(word.slice(0, -2), VERB);
  if (word.endsWith("는가") && word.length > 2) return classifyPredicate(word.slice(0, -2), previous, QUESTION);
  if (word.endsWith("자") && word.length > 1) {
    const stem = restoreRieul(word.slice(0, -1));
    if (stem.endsWith("하") || stem.endsWith("보") || rieulStems().has(stem)) {
      return predicate(stem, VERB, PRESENT, PROPOSITIVE);
    }
  }
  if (word.endsWith("다") && word.length > 1) {
    const stem = word.slice(0, -1);
    const last = stem.at(-1);
    if (hangul.isSyllable(last) && hangul.finalOf(last) === hangul.NIEUN && !word.endsWith("이다")) {
      return predicate(restoreRieul(stemBefore(stem, 1)), VERB);
    }
    const tense = tenseOf(stem);
    if (tense !== PRESENT) return predicate(stem, VERB, tense);
    if (word.endsWith("이다") && word.length > 2) return predicate(word.slice(0, -2), COPULA, PRESENT, DECLARATIVE, true);
    if (stem === "않") return predicate(stem, kindOf(stem, previous));
    if (isAdjective(stem)) return predicate(stem, ADJECTIVE);
    return predicate(stem, COPULA);
  }
  return null;
}

/** 어간에 아/어를 붙인 꼴. @param {string} stem */
export function conjugate(stem) {
  if (stem === "아니") return "아니에";
  if (stem.endsWith("하")) return stem.slice(0, -1) + "해";
  const last = hangul.lastSyllable(stem);
  if (last === null) return stem + "어";
  const [, vowel, final] = hangul.split(last);
  const kind = irregularClass(stem);
  if (kind === "르" && stem.length >= 2 && hangul.isSyllable(stem.at(-2))) {
    const before = stem.at(-2);
    const bright = hangul.BRIGHT.has(hangul.vowelOf(before));
    return stem.slice(0, -2) + hangul.withFinal(before, hangul.RIEUL) + (bright ? "라" : "러");
  }
  if (kind === "ㅂ") return stem.slice(0, -1) + hangul.withFinal(last, hangul.NONE) + "워";
  if (kind === "ㅂ와") return stem.slice(0, -1) + hangul.withFinal(last, hangul.NONE) + "와";
  if (kind === "ㄷ") return stem.slice(0, -1) + hangul.withFinal(last, hangul.RIEUL) + (hangul.BRIGHT.has(vowel) ? "아" : "어");
  if (kind === "ㅅ") return stem.slice(0, -1) + hangul.withFinal(last, hangul.NONE) + (hangul.BRIGHT.has(vowel) ? "아" : "어");
  if (kind === "ㅎ") {
    for (const [known, changed] of HAE_IRREGULAR) {
      if (stem.endsWith(known)) return stem.slice(0, -known.length) + changed;
    }
    const opened = hangul.withFinal(last, hangul.NONE);
    const target = new Map([
      [hangul.A, hangul.AE],
      [hangul.YA, hangul.YAE],
      [hangul.EO, hangul.E],
      [hangul.YEO, hangul.YE],
    ]).get(vowel) ?? hangul.AE;
    return stem.slice(0, -1) + hangul.withVowel(opened, target);
  }
  if (final !== hangul.NONE) return stem + (hangul.BRIGHT.has(vowel) ? "아" : "어");
  if ([hangul.A, hangul.YA, hangul.EO, hangul.YEO, hangul.AE, hangul.E, hangul.YE].includes(vowel)) return stem;
  if (vowel === hangul.OH) return stem.slice(0, -1) + hangul.withVowel(last, hangul.WA);
  if (vowel === hangul.U) return stem.slice(0, -1) + hangul.withVowel(last, hangul.WO);
  if (vowel === hangul.OE) return stem.slice(0, -1) + hangul.withVowel(last, hangul.WAE);
  if (vowel === hangul.IH) return stem.slice(0, -1) + hangul.withVowel(last, hangul.YEO);
  if (vowel === hangul.EU) {
    const before = stem.length >= 2 && hangul.isSyllable(stem.at(-2)) ? stem.at(-2) : null;
    const bright = before !== null && hangul.BRIGHT.has(hangul.vowelOf(before));
    return stem.slice(0, -1) + hangul.withVowel(last, bright ? hangul.A : hangul.EO);
  }
  return stem + "어";
}

/** @param {string} stem */
function hasFinal(stem) {
  const last = hangul.lastSyllable(stem);
  return last !== null ? hangul.finalOf(last) : hangul.MIEUM;
}

/** @param {string} stem */
function polite(stem) {
  const final = hasFinal(stem);
  if (final === hangul.NONE || final === hangul.RIEUL) {
    return stem.slice(0, -1) + hangul.withFinal(stem.at(-1), hangul.BIEUP) + "니다";
  }
  return stem + "습니다";
}

/** @param {string} stem */
function plainVerb(stem) {
  const final = hasFinal(stem);
  if (final === hangul.NONE || final === hangul.RIEUL) {
    return stem.slice(0, -1) + hangul.withFinal(stem.at(-1), hangul.NIEUN) + "다";
  }
  return stem + "는다";
}

/** @param {string} stem @param {string} ending */
function withEu(stem, ending) {
  const final = hasFinal(stem);
  if (final === hangul.NONE) return stem + ending;
  if (final === hangul.RIEUL) {
    const base = ending === "세요" ? stem.slice(0, -1) + hangul.withFinal(stem.at(-1), hangul.NONE) : stem;
    return base + ending;
  }
  const kind = irregularClass(stem);
  const last = stem.at(-1);
  if (kind === "ㅂ" || kind === "ㅂ와") return stem.slice(0, -1) + hangul.withFinal(last, hangul.NONE) + "우" + ending;
  if (kind === "ㄷ") return stem.slice(0, -1) + hangul.withFinal(last, hangul.RIEUL) + "으" + ending;
  if (kind === "ㅅ") return stem.slice(0, -1) + hangul.withFinal(last, hangul.NONE) + "으" + ending;
  return stem + "으" + ending;
}

/** 서술어를 target 문체로 짠다. @param {Predicate} value @param {string} target */
export function render(value, target) {
  const { base, kind, tense, mood } = value;
  if (mood === KKA_QUESTION) return target === HANDA ? base : base + "요";
  if (tense !== PRESENT) {
    if (target === HAPNIDA) return base + (mood === QUESTION ? "습니까" : "습니다");
    if (target === HANDA) return base + (mood === QUESTION ? "는가" : "다");
    return base + "어요";
  }
  if (kind === COPULA) {
    if (!base) return { [HAPNIDA]: "입니다", [HANDA]: "다", [HAEYO]: "예요" }[target];
    const final = hasFinal(base);
    if (target === HAPNIDA) return base + (mood === QUESTION ? "입니까" : "입니다");
    if (target === HANDA) {
      if (mood === QUESTION) return base + "인가";
      return base + (value.explicitCopula || final !== hangul.NONE ? "이다" : "다");
    }
    return base + (final !== hangul.NONE ? "이에요" : "예요");
  }
  if (mood === IMPERATIVE) return target === HANDA ? withEu(base, "라") : withEu(base, "세요");
  if (mood === PROPOSITIVE) {
    if (target === HAPNIDA) {
      const final = hasFinal(base);
      if (final === hangul.NONE || final === hangul.RIEUL) {
        return base.slice(0, -1) + hangul.withFinal(base.at(-1), hangul.BIEUP) + "시다";
      }
      return base + "읍시다";
    }
    if (target === HANDA) return base + "자";
    return conjugate(base) + "요";
  }
  if (target === HAPNIDA) {
    const form = polite(base);
    return mood === QUESTION ? form.slice(0, -2) + "니까" : form;
  }
  if (target === HANDA) {
    if (kind === ADJECTIVE) {
      if (mood === QUESTION) {
        const final = hasFinal(base);
        if (final === hangul.NONE || final === hangul.RIEUL) {
          return base.slice(0, -1) + hangul.withFinal(base.at(-1), hangul.NIEUN) + "가";
        }
        return base + "은가";
      }
      return base + "다";
    }
    if (mood === QUESTION) {
      const stem = hasFinal(base) === hangul.RIEUL ? base.slice(0, -1) + hangul.withFinal(base.at(-1), hangul.NONE) : base;
      return stem + "는가";
    }
    return plainVerb(base);
  }
  return conjugate(base) + "요";
}
