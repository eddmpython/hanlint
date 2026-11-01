// @ts-check
/**
 * 문장에서 정해 둔 말을 센다. 종결어미 묶음, 서법, 접속부사, 인과 접속사, 지시어, 얼버무리는 말, 약속하는 말과 다시 다루는 말, 독자 호출, 수 약속.
 * 단어 목록은 모두 data/에 있다. 파이썬 fingerprint/markers.py와 같다.
 */
import { loadLines, loadPatterns } from "../data/load.js";
import { compile, escape } from "../regex.js";

const TRAILING = /[\s.?!"'”’)\]]+$/;
const NUMBER = /\d+(?:[.,]\d+)*/g;
/** 값으로 비교하는 수. NUMBER는 수의 개수를 세고 이것은 수의 정체를 센다. 천 단위 쉼표까지 한 수로 읽는다. */
const NUMERAL = /\d[\d,]*(?:\.\d+)?/g;
const COMMA = /,/g;
// 따옴표 쌍. 안은 사용이 아니라 인용이다. 작은따옴표는 앞이 문장 첫머리나 공백이나 여는 괄호일 때만.
const QUOTE_PAIRS = [
  /"([^"\n]{1,80})"/g,
  /“([^“”\n]{1,80})”/g,
  /‘([^‘’\n]{1,80})’/g,
  /「([^「」\n]{1,80})」/g,
  /『([^『』\n]{1,80})』/g,
  /(?<=^|[\s(])'([^'\n]{1,80})'/g,
];
const CONNECTOR_LOOKAHEAD = /(?=[\s,])/.source;
const NO_HANGUL_BEFORE = /(?<![가-힣])/.source;
const DIGITS = /\d+/.source;
const OPTIONAL_SPACE = /\s?/.source;

/** @type {Record<string, number> | null} */
let numberCache = null;
/** 수사 → 값. 목록은 data/koreanNumbers.txt에 있다. */
export function koreanNumbers() {
  if (!numberCache) {
    numberCache = {};
    for (const line of loadLines("koreanNumbers.txt")) {
      const [word, value] = line.split("\t");
      numberCache[word] = parseInt(value, 10);
    }
  }
  return numberCache;
}

/** @type {[string, import("../regex.js").Pattern][] | null} */
let endingCache = null;
export function endingClasses() {
  if (!endingCache) {
    endingCache = loadLines("endings.txt").map((line) => {
      const at = line.indexOf("\t");
      return [line.slice(0, at), compile(line.slice(at + 1))];
    });
  }
  return endingCache;
}

/** @type {import("../regex.js").Pattern | null} */
let connectorCache = null;
export function connectorPattern() {
  if (!connectorCache) {
    const names = [...loadLines("connectors.txt")].sort((a, b) => b.length - a.length);
    connectorCache = compile(`^(${names.map(escape).join("|")})${CONNECTOR_LOOKAHEAD}`);
  }
  return connectorCache;
}

/** @type {import("../regex.js").Pattern | null} */
let countCache = null;
export function countPromisePattern() {
  if (!countCache) {
    const units = loadLines("countUnits.txt").map(escape).join("|");
    const numbers = Object.keys(koreanNumbers())
      .sort((a, b) => b.length - a.length)
      .join("|");
    // 단위 뒤에는 조사가 붙는 것이 정상이다 (여섯 가지를). 앞쪽만 경계를 본다.
    countCache = compile(`${NO_HANGUL_BEFORE}(${numbers}|${DIGITS})${OPTIONAL_SPACE}(${units})`);
  }
  return countCache;
}

/** @param {string} text */
export function stripTrailing(text) {
  return text.trim().replace(TRAILING, "");
}

/** @param {string} text */
export function endingOf(text) {
  const body = stripTrailing(text);
  for (const [kind, pattern] of endingClasses()) {
    if (pattern.search(body)) return kind;
  }
  return "없음";
}

/** @param {string} text @param {string} ending */
export function moodOf(text, ending) {
  const stripped = text.trim();
  if (stripped.endsWith("?") || ending === "의문") return "의문";
  if (ending === "명령") return "명령";
  return "평서";
}

/** @param {string} text */
export function connectorStartOf(text) {
  const match = connectorPattern().at(text.trim());
  return match ? match[1] : null;
}

/** @param {string} text @param {string} patternFile */
export function countMatches(text, patternFile) {
  let total = 0;
  for (const pattern of loadPatterns(patternFile)) total += pattern.all(text).length;
  return total;
}

/** @param {string} text @param {string} patternFile @returns {string[]} */
export function matchedTexts(text, patternFile) {
  /** @type {string[]} */
  const found = [];
  for (const pattern of loadPatterns(patternFile)) {
    for (const match of pattern.all(text)) found.push(match[0]);
  }
  return found;
}

/** (시작, 끝, 원문). 인용 구간 안의 것을 거를 때 쓴다. @param {string} text @param {string} patternFile @returns {[number, number, string][]} */
export function matchedSpans(text, patternFile) {
  /** @type {[number, number, string][]} */
  const found = [];
  for (const pattern of loadPatterns(patternFile)) {
    for (const match of pattern.all(text)) {
      const start = /** @type {number} */ (match.index);
      found.push([start, start + match[0].length, match[0]]);
    }
  }
  return found;
}

/** 따옴표 쌍 안의 [시작, 끝]. 인용은 사용이 아니다. @param {string} text @returns {[number, number][]} */
export function quoteSpans(text) {
  /** @type {[number, number][]} */
  const found = [];
  for (const pattern of QUOTE_PAIRS) {
    pattern.lastIndex = 0;
    for (const match of text.matchAll(pattern)) {
      const start = /** @type {number} */ (match.index) + match[0].indexOf(match[1]);
      found.push([start, start + match[1].length]);
    }
  }
  return found.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
}

/**
 * 설정의 protectedTerms가 글에 나온 [시작, 끝] 전부. 겹쳐 나온 것도 따로 센다. 파이썬 termSpans와 같다.
 * @param {string} text @param {string[]} terms @returns {[number, number][]}
 */
export function termSpans(text, terms) {
  /** @type {[number, number][]} */
  const found = [];
  for (const term of terms) {
    let start = text.indexOf(term);
    while (start !== -1) {
      found.push([start, start + term.length]);
      start = text.indexOf(term, start + 1);
    }
  }
  return found.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
}

/** 두 구간이 한 글자라도 겹치는가. 파이썬 overlapsAny와 같다. @param {number} start @param {number} end @param {[number, number][]} spans */
export function overlapsAny(start, end, spans) {
  return spans.some(([spanStart, spanEnd]) => spanStart < end && start < spanEnd);
}

/** @param {number} start @param {number} end @param {[number, number][]} spans */
export function insideAny(start, end, spans) {
  return spans.some(([spanStart, spanEnd]) => spanStart <= start && end <= spanEnd);
}

/** @param {string} text @returns {[number, string, string][]} (수, 단위, 원문) */
export function countPromisesIn(text) {
  /** @type {[number, string, string][]} */
  const found = [];
  for (const match of countPromisePattern().all(text)) {
    const raw = match[1];
    const unit = match[2];
    if (/^\d+$/.test(raw) && unit === "단계" && !match[0].includes(" ")) continue;
    const number = koreanNumbers()[raw] ?? parseInt(raw, 10);
    found.push([number, unit, match[0]]);
  }
  return found;
}

/** @param {string} text */
/** 글에 나온 수의 정체 (천 단위 쉼표를 뗀 꼴). 독자 상태가 쌓고 numberOrphan이 비교한다. @param {string} text @returns {Set<string>} */
export function numeralsIn(text) {
  const found = new Set();
  for (const match of text.matchAll(NUMERAL)) found.add(match[0].replaceAll(",", ""));
  return found;
}

export function countNumbers(text) {
  return [...text.matchAll(NUMBER)].length;
}

/** @param {string} text */
export function countCommas(text) {
  return [...text.matchAll(COMMA)].length;
}
