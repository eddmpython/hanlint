// @ts-check
import { DOCUMENT, NOTICE, finding } from "../finding.js";

export const name = "keywordHeading";
/** 목차라고 부를 수 있는 최소 H2 수. 둘 이하는 훑을 목차가 아니다. */
const MIN_HEADINGS = 3;
/** 한 글자 낱말은 어느 제목에나 우연히 들어 있어 가르지 못한다. */
const MIN_WORD = 2;

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  if (!config.keywordField) return [];
  const keyword = (doc.frontmatter[config.keywordField] ?? "").trim();
  const title = doc.frontmatter.title ?? "";
  const headings = doc.headings.filter(([level]) => level === 2);
  if (!keyword || headings.length < MIN_HEADINGS) return [];
  const joined = headings.map(([, text]) => text).join(" / ");
  const missing = keyword.split(/\s+/).filter((word) => word.length >= MIN_WORD && title.includes(word) && !joined.includes(word));
  if (!missing.length) return [];
  return [
    finding(name, headings[0][2], joined, `제목이 약속한 \`${missing[0]}\` 가 절 제목 어디에도 없다. 목차를 훑는 독자가 이 글이 그것을 다루는지 못 본다`, null, NOTICE, DOCUMENT, -1),
  ];
}
