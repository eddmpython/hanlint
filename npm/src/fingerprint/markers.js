// @ts-check
/**
 * 문장에서 표지를 센다. 종결어미 부류, 서법, 접속부사, 인과, 지시어, 헤지, 약속과 회수, 독자 호출, 수 약속.
 * 낱말 목록은 전부 data/ 가 정본이다. 파이썬 fingerprint/markers.py 와 같다.
 */
import { loadLines, loadPatterns } from "../data/load.js";
import { compile, escape } from "../regex.js";

const TRAILING = /[\s.?!"'”’)\]]+$/;
const NUMBER = /\d+(?:[.,]\d+)*/g;
const COMMA = /,/g;
const CONNECTOR_LOOKAHEAD = /(?=[\s,])/.source;
const NO_HANGUL_BEFORE = /(?<![가-힣])/.source;
const DIGITS = /\d+/.source;
const OPTIONAL_SPACE = /\s?/.source;

/** @type {Record<string, number> | null} */
let numberCache = null;
/** 수사 → 값. 정본은 data/koreanNumbers.txt. */
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
export function countNumbers(text) {
  return [...text.matchAll(NUMBER)].length;
}

/** @param {string} text */
export function countCommas(text) {
  return [...text.matchAll(COMMA)].length;
}
