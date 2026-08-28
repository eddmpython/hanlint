// @ts-check
/**
 * 문서 모델. 세 층이다. Block (빈 줄로 나뉜 덩어리), Section (H2 하나가 여는 절), Document (전체).
 * 줄 번호는 1 부터 세고 원문 기준이다.
 */

export const PROSE = "prose";
export const HEADING = "heading";
export const CODE = "code";
export const QUOTE = "quote";
export const IMAGE = "image";
export const LIST = "list";
export const TABLE = "table";
export const EMBED = "embed";
export const HTML = "html";

/**
 * @typedef {object} Block
 * @property {string} kind
 * @property {number} startLine
 * @property {number} endLine
 * @property {string} text
 * @property {number} level heading 일 때 `#` 의 개수
 * @property {number} index 문서 안 순서
 */

/**
 * @typedef {object} Section
 * @property {Block | null} heading
 * @property {Block[]} blocks
 */

/**
 * @typedef {object} Document
 * @property {string | null} path
 * @property {Record<string, string>} frontmatter
 * @property {Block[]} blocks
 * @property {Section[]} sections
 * @property {[string, number, number][]} disabled 인라인 제어가 끈 (규칙 또는 *, 시작 줄, 끝 줄)
 * @property {Block[]} ignored 설정이 지문에서 뺀 펜스. 파일 전체를 보는 규칙만 읽는다
 */

/** @param {Section} section */
export function sectionTitle(section) {
  return section.heading ? section.heading.text : "";
}

/** @param {Section} section */
export function sectionStartLine(section) {
  if (section.heading) return section.heading.startLine;
  return section.blocks.length ? section.blocks[0].startLine : 1;
}

/** @param {Document} doc @param {number | null} [level] */
export function headingsOf(doc, level = null) {
  return doc.blocks.filter((b) => b.kind === HEADING && (level === null || b.level === level));
}
