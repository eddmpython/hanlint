// @ts-check
/** 지적 하나의 모양. 파이썬 rules/finding.py 와 같은 필드와 같은 JSON 순서다. */

export const ERROR = "error";
export const NOTICE = "notice";

export const SENTENCE = "sentence";
export const PARAGRAPH = "paragraph";
export const SECTION = "section";
export const DOCUMENT = "document";

/**
 * @typedef {object} Finding
 * @property {string} rule
 * @property {number} line
 * @property {string} quote
 * @property {string} why
 * @property {string | null} fix 기계가 낼 수 있을 때만
 * @property {string} severity error 는 규칙 위반, notice 는 확인이 필요한 것
 * @property {string} scope sentence, paragraph, section, document
 * @property {number} at scope 가 가리키는 지문의 index
 */

/**
 * @param {string} rule
 * @param {number} line
 * @param {string} quote
 * @param {string} why
 * @param {string | null} [fix]
 * @param {string} [severity]
 * @param {string} [scope]
 * @param {number} [at]
 * @returns {Finding}
 */
export function finding(rule, line, quote, why, fix = null, severity = ERROR, scope = SENTENCE, at = -1) {
  return { rule, line, quote, why, fix, severity, scope, at };
}

/** @param {Finding} f */
export function findingAsDict(f) {
  /** @type {Record<string, unknown>} */
  const data = { rule: f.rule, line: f.line, severity: f.severity, scope: f.scope, at: f.at, quote: f.quote, why: f.why };
  if (f.fix) data.fix = f.fix;
  return data;
}
