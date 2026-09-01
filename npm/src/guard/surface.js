// @ts-check
/** 계약 본문과 결과 글 사이의 보호 원자 차이. */

const NUMBER_ATOM = /(?<!\p{Nd})(?:\p{Nd}{1,3}(?:,\p{Nd}{3})+|\p{Nd}+)(?:\.\p{Nd}+)*(?!\p{Nd})/gu;
const URL = /https?:\/\/[^\s)>\]]*[\p{L}\p{N}_\/#=%&+~-]/gu;
const INLINE_CODE = /`([^`\n]+)`/gu;
const LINK_DESTINATION = /\[[^\u005D]*\]\(([^)]+)\)/gu;
const DECIMAL_ZEROS = [
  0x0030, 0x0660, 0x06f0, 0x07c0, 0x0966, 0x09e6, 0x0a66, 0x0ae6, 0x0b66, 0x0be6,
  0x0c66, 0x0ce6, 0x0d66, 0x0de6, 0x0e50, 0x0ed0, 0x0f20, 0x1040, 0x1090, 0x17e0,
  0x1810, 0x1946, 0x19d0, 0x1a80, 0x1a90, 0x1b50, 0x1bb0, 0x1c40, 0x1c50, 0xa620,
  0xa8d0, 0xa900, 0xa9d0, 0xa9f0, 0xaa50, 0xabf0, 0xff10, 0x104a0, 0x10d30, 0x11066,
  0x110f0, 0x11136, 0x111d0, 0x112f0, 0x11450, 0x114d0, 0x11650, 0x116c0, 0x11730, 0x118e0,
  0x11950, 0x11c50, 0x11d50, 0x11da0, 0x16a60, 0x16ac0, 0x16b50, 0x1d7ce, 0x1e140, 0x1e2f0,
  0x1e4f0, 0x1e950,
];

/** 파이썬 문자열 순서와 같은 코드 포인트 순서. @param {string} left @param {string} right */
export function compareText(left, right) {
  const leftPoints = [...left].map((value) => /** @type {number} */ (value.codePointAt(0)));
  const rightPoints = [...right].map((value) => /** @type {number} */ (value.codePointAt(0)));
  const limit = Math.min(leftPoints.length, rightPoints.length);
  for (let index = 0; index < limit; index += 1) {
    if (leftPoints[index] !== rightPoints[index]) return leftPoints[index] - rightPoints[index];
  }
  return leftPoints.length - rightPoints.length;
}

/** @param {string} character */
function decimalValue(character) {
  const point = /** @type {number} */ (character.codePointAt(0));
  const zero = DECIMAL_ZEROS.find((start) => start <= point && point < start + 10);
  if (zero === undefined) throw new Error(`지원하지 않는 유니코드 십진 숫자다: ${character}`);
  return String(point - zero);
}

/** @param {string} value */
function canonicalNumber(value) {
  return [...value]
    .filter((character) => character !== ",")
    .map((character) => (/\p{Nd}/u.test(character) ? decimalValue(character) : character))
    .join("");
}

/** @param {string} text */
export function numberValues(text) {
  return [...new Set([...text.matchAll(NUMBER_ATOM)].map((match) => canonicalNumber(match[0])))].sort(compareText);
}

/** @param {RegExp} pattern @param {string} text */
function valuesOf(pattern, text) {
  return [...new Set([...text.matchAll(pattern)].map((match) => (match.length > 1 ? match[1] : match[0])))].sort(compareText);
}

/** @param {string[]} expected @param {string[]} actual */
function difference(expected, actual) {
  const other = new Set(actual);
  return expected.filter((value) => !other.has(value)).sort(compareText);
}

/** @param {string} contractText @param {string} text @param {string[] | null} [numbers] */
export function surfaceDiff(contractText, text, numbers = null) {
  const surfaceText = text.normalize("NFC");
  const expectedNumbers = numbers === null ? numberValues(contractText) : [...new Set(numbers)].sort(compareText);
  const actualNumbers = numberValues(surfaceText);
  const expectedUrls = valuesOf(URL, contractText);
  const actualUrls = valuesOf(URL, surfaceText);
  const expectedCode = valuesOf(INLINE_CODE, contractText);
  const actualCode = valuesOf(INLINE_CODE, surfaceText);
  const expectedLinks = valuesOf(LINK_DESTINATION, contractText);
  const actualLinks = valuesOf(LINK_DESTINATION, surfaceText);
  const allowedCode = [...new Set([...expectedCode, ...actualCode.filter((value) => contractText.includes(value))])];
  const allowedLinks = [...new Set([...expectedLinks, ...actualLinks.filter((value) => contractText.includes(value))])];
  return {
    missingNumbers: difference(expectedNumbers, actualNumbers),
    unexpectedNumbers: difference(actualNumbers, expectedNumbers),
    missingUrls: difference(expectedUrls, actualUrls),
    unexpectedUrls: difference(actualUrls, expectedUrls),
    missingCode: difference(expectedCode, actualCode),
    unexpectedCode: difference(actualCode, allowedCode),
    missingLinks: difference(expectedLinks, actualLinks),
    unexpectedLinks: difference(actualLinks, allowedLinks),
  };
}

/** @param {ReturnType<typeof surfaceDiff>} diff */
export function surfaceViolationCount(diff) {
  return Object.values(diff).reduce((total, values) => total + values.length, 0);
}
