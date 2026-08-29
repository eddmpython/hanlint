// @ts-check
/**
 * 어절 단위 근사. 조사와 어미 꼬리 사전으로 명사 어절을 가려낸다. 파이썬 analysis/tokenize.py 와 같은 판정이다.
 * 띄어 쓴 조사와 계사는 앞 어절에 붙은 것으로, 영문 어절 연속은 한 덩어리로, 수사와 바로 뒤 단위는 수량으로 본다.
 */
import { loadLines } from "../data/load.js";
import { splitWords, stripChars } from "../text.js";

const HANGUL = /[가-힣]/;
const HANGUL_WORD = /^[가-힣]+$/;
const WORD_CHARS = /^[가-힣A-Za-z0-9]+$/;
/** 관형격 조사 의. 영문과 숫자 뒤 (API의, 600MiB의) 와 닫는 괄호 뒤 (L7(HTTP)의) 도 센다. 파이썬 tokenize.py 와 같다. */
const GENITIVE = /([가-힣A-Za-z0-9]+|\))의(?=[\s,.)\]]|$)/g;
const SPACED_GENITIVE = /(?<=\s)의(?=\s)/g;
const COPULA = /^(?:이(?:고|며|다|라|란|면|라서|므로|지만|어서|었다|었고)|인|인데|입니다|였다)$/;
const DIGITS = /^\d+$/;
/** 수에 단위가 붙은 어절 (2012년, 30분쯤, 제16호, 100명). 수량이라 명사 나열에서 세지도 끊지도 않는다. */
const QUANTITY = /^제?\d[\d,.]*[가-힣]{1,3}$/;
const OPENERS = "([{\"“‘'";
const CLOSERS = ",.?!;:)]}\"”’'";
const EDGE_PUNCTUATION = ".,?!:;\"'“”‘’()[]{}<>";

/**
 * @typedef {object} Word
 * @property {string} core 앞뒤 부호를 뗀 어절
 * @property {boolean} endsClause 뒤에 쉼표, 종결 부호, 닫는 괄호가 붙어 있었는가
 * @property {boolean} opens 앞에 여는 괄호나 따옴표가 있었는가
 * @property {boolean} particle 띄어 쓴 조사나 계사인가
 */

/** @type {Map<string, string[]>} */
const tailCache = new Map();

/** 긴 것부터. @param {string} name */
export function tails(name) {
  let sorted = tailCache.get(name);
  if (!sorted) {
    sorted = [...loadLines(name)].sort((a, b) => b.length - a.length);
    tailCache.set(name, sorted);
  }
  return sorted;
}

/** @type {Set<string> | null} */
let josaCache = null;
export function josaSet() {
  if (!josaCache) josaCache = new Set(loadLines("josa.txt"));
  return josaCache;
}

/** @type {Set<string> | null} */
let euiNounCache = null;
export function euiNouns() {
  if (!euiNounCache) euiNounCache = new Set(loadLines("euiNouns.txt"));
  return euiNounCache;
}

/** @type {Set<string> | null} */
let numeralCache = null;
export function numerals() {
  if (!numeralCache) numeralCache = new Set(loadLines("koreanNumbers.txt").map((line) => line.split("\t")[0]));
  return numeralCache;
}

/** @type {Set<string> | null} */
let nonNounCache = null;
export function nonNouns() {
  if (!nonNounCache) nonNounCache = new Set(loadLines("nonNouns.txt"));
  return nonNounCache;
}

/** @type {Set<string> | null} */
let inNounCache = null;
export function inNouns() {
  if (!inNounCache) inNounCache = new Set(loadLines("inNouns.txt"));
  return inNounCache;
}

/**
 * `도구인`, `규모인` 처럼 명사에 계사 관형형 인 이 붙은 어절. 서술어라 명사 나열을 끊는다. 어간이 두 음절 이상일 때만이고
 * 외국인 같은 세 음절 명사는 data/inNouns.txt 가 뺀다. 파이썬 tokenize.py 와 같다.
 * @param {string} core
 */
export function isCopulaAdnominal(core) {
  return core.length >= 3 && core.endsWith("인") && HANGUL_WORD.test(core) && !inNouns().has(core);
}

/** @param {string} core */
export function isNumeral(core) {
  return numerals().has(core) || DIGITS.test(core);
}

/** 단위가 붙은 수. 수사와 달리 뒤 어절을 단위로 삼지 않는다. @param {string} core */
export function isQuantity(core) {
  return QUANTITY.test(core);
}

/** @param {string} text @returns {Word[]} */
export function words(text) {
  return splitWords(text).map((raw) => {
    const core = stripChars(raw, EDGE_PUNCTUATION);
    const particle = josaSet().has(core) || COPULA.test(core);
    return { core, endsClause: CLOSERS.includes(raw[raw.length - 1]), opens: OPENERS.includes(raw[0]), particle };
  });
}

/** @param {string} core @param {string} name */
export function tailOf(core, name) {
  for (const tail of tails(name)) {
    if (core.endsWith(tail) && core.length > tail.length) return tail;
  }
  return null;
}

/** @param {string} core */
export function stripJosa(core) {
  const tail = tailOf(core, "josa.txt");
  return tail ? core.slice(0, -tail.length) : core;
}

/** 조사도 어미도 붙지 않은 한글, 영문, 숫자 어절인가. @param {string} core */
export function isBareNoun(core) {
  if (!core || !WORD_CHARS.test(core)) return false;
  if (!HANGUL.test(core)) return true;
  return tailOf(core, "josa.txt") === null && tailOf(core, "verbTails.txt") === null;
}

/**
 * 명사 어절 연속의 최대 길이. 의존명사와 관형사와 부사 (`수`, `몇`, `직접`) 는 조사도 어미도 안 붙어
 * 표층으로는 명사로 보이지만 명사 쌓기의 재료가 아니다. data/nonNouns.txt 가 그 목록이고 연속을 끊는다.
 * @param {string} text
 */
export function longestNounRun(text) {
  let longest = 0;
  let run = 0;
  let previousAscii = false;
  let afterNumeral = false;
  for (const word of words(text)) {
    if (word.opens) {
      run = 0;
      previousAscii = false;
    }
    const transparent = isNumeral(word.core) || afterNumeral || isQuantity(word.core);
    afterNumeral = isNumeral(word.core);
    if (word.particle || nonNouns().has(word.core) || !isBareNoun(word.core) || isCopulaAdnominal(word.core)) {
      run = 0;
      previousAscii = false;
    } else if (!transparent) {
      const isAscii = !HANGUL.test(word.core);
      if (!(isAscii && previousAscii)) run += 1;
      previousAscii = isAscii;
      longest = Math.max(longest, run);
    }
    if (word.endsClause) {
      run = 0;
      previousAscii = false;
    }
  }
  return longest;
}

/** 관형격 조사 의 가 붙은 자리 [시작, 끝]. 정의, 회의 처럼 의 로 끝나는 낱말은 빼고 띄어 쓴 의 는 넣는다. @param {string} text @returns {[number, number][]} */
export function genitiveSpans(text) {
  /** @type {[number, number][]} */
  const spans = [];
  for (const match of text.matchAll(GENITIVE)) {
    if (!euiNouns().has(match[1] + "의")) spans.push([/** @type {number} */ (match.index), /** @type {number} */ (match.index) + match[0].length]);
  }
  for (const match of text.matchAll(SPACED_GENITIVE)) spans.push([/** @type {number} */ (match.index), /** @type {number} */ (match.index) + match[0].length]);
  return spans.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
}

/** 의 로 끝나는 어절 둘이 붙어 있는가 (회사의 팀의). 사이가 공백뿐이어야 한다. @param {string} text */
export function euiAdjacent(text) {
  const spans = genitiveSpans(text);
  return spans.some((span, index) => index > 0 && /^\s+$/.test(text.slice(spans[index - 1][1], span[0])));
}

/** 관형격 조사 의 의 수. @param {string} text */
export function euiCount(text) {
  return genitiveSpans(text).length;
}

/** 초성과 중성이 정해진 한글 음절 28개의 정규식 범위. @param {number} initial @param {number} vowel */
export function syllableRange(initial, vowel) {
  const first = 0xac00 + (initial * 21 + vowel) * 28;
  return `${String.fromCharCode(first)}-${String.fromCharCode(first + 27)}`;
}

const PASSIVE_TAIL = `[${syllableRange(12, 20)}${syllableRange(12, 6)}]`;

/** @type {RegExp | null} */
let passivePattern = null;
export function doublePassivePattern() {
  if (!passivePattern) {
    const stems = ["되어"];
    const contraction = { 이: "여", 히: "혀", 리: "려", 기: "겨" };
    for (const stem of loadLines("passiveStems.txt")) {
      const last = stem[stem.length - 1];
      stems.push(last in contraction ? stem.slice(0, -1) + contraction[last] : `${stem}어`);
    }
    const alternatives = [...stems].sort((a, b) => b.length - a.length).join("|");
    passivePattern = new RegExp(`(${alternatives})${PASSIVE_TAIL}`, "g");
  }
  return passivePattern;
}

/** 이중 피동의 표층형을 `되어지` 꼴로. @param {string} text */
export function doublePassives(text) {
  return [...text.matchAll(doublePassivePattern())].map((match) => `${match[1]}지`);
}
