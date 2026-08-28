// @ts-check
/**
 * 한글 음절의 자모 산술. 파이썬 `analysis/grammar/hangul.py` 의 투영이다. 표 대신 산술로 하는 까닭은 그 파일이 소유한다.
 */

export const BASE = 0xac00;
export const LAST = 0xd7a3;
export const VOWELS = 21;
export const FINALS = 28;

// 중성 자리 번호. ㅏ ㅐ ㅑ ㅒ ㅓ ㅔ ㅕ ㅖ ㅗ ㅘ ㅙ ㅚ ㅛ ㅜ ㅝ ㅞ ㅟ ㅠ ㅡ ㅢ ㅣ 차례다.
export const A = 0;
export const AE = 1;
export const YA = 2;
export const YAE = 3;
export const EO = 4;
export const E = 5;
export const YEO = 6;
export const YE = 7;
export const OH = 8;
export const WA = 9;
export const WAE = 10;
export const OE = 11;
export const YO = 12;
export const U = 13;
export const WO = 14;
export const WE = 15;
export const WI = 16;
export const YU = 17;
export const EU = 18;
export const UI = 19;
export const IH = 20;

// 종성 자리 번호 가운데 형태 층이 이름으로 부르는 것.
export const NONE = 0;
export const GIYEOK = 1;
export const NIEUN = 4;
export const DIGEUT = 7;
export const RIEUL = 8;
export const MIEUM = 16;
export const BIEUP = 17;
export const SIOT = 19;
export const SSANGSIOT = 20;
export const IEUNG = 21;
export const HIEUT = 27;

/** 양성 모음. 이 모음 뒤에는 `아` 가 붙고 나머지에는 `어` 가 붙는다. */
export const BRIGHT = new Set([A, OH, YA, YO, WA]);

/** @param {string} ch */
export function isSyllable(ch) {
  if (ch.length !== 1) return false;
  const code = ch.charCodeAt(0);
  return code >= BASE && code <= LAST;
}

/** (초성, 중성, 종성) 자리 번호. @param {string} ch @returns {[number, number, number]} */
export function split(ch) {
  if (!isSyllable(ch)) throw new Error(`한글 음절이 아니다: ${JSON.stringify(ch)}`);
  const code = ch.charCodeAt(0) - BASE;
  return [Math.floor(code / (VOWELS * FINALS)), Math.floor(code / FINALS) % VOWELS, code % FINALS];
}

/** @param {number} initial @param {number} vowel @param {number} [final] */
export function join(initial, vowel, final = NONE) {
  return String.fromCharCode(BASE + (initial * VOWELS + vowel) * FINALS + final);
}

/** 음절의 종성 번호. 한글 음절이 아니면 null. @param {string} ch */
export function finalOf(ch) {
  return isSyllable(ch) ? split(ch)[2] : null;
}

/** @param {string} ch */
export function vowelOf(ch) {
  return isSyllable(ch) ? split(ch)[1] : null;
}

/** @param {string} ch @param {number} final */
export function withFinal(ch, final) {
  const [initial, vowel] = split(ch);
  return join(initial, vowel, final);
}

/** @param {string} ch @param {number} vowel */
export function withVowel(ch, vowel) {
  const [initial, , final] = split(ch);
  return join(initial, vowel, final);
}

/** 낱말의 마지막 한글 음절. 없으면 null. @param {string} word */
export function lastSyllable(word) {
  return word && isSyllable(word[word.length - 1]) ? word[word.length - 1] : null;
}
