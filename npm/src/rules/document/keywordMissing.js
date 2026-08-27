// @ts-check
import { DOCUMENT, finding } from "../finding.js";

export const name = "keywordMissing";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  if (!config.keywordField) return [];
  const keyword = (doc.frontmatter[config.keywordField] ?? "").trim();
  if (!keyword) return [];
  const title = doc.frontmatter.title ?? "";
  const first = doc.paragraphs.length ? doc.paragraphs[0] : null;
  const head = `${title}\n${first ? first.text : ""}`;
  if (head.includes(keyword)) return [];
  return [
    finding(name, first ? first.startLine : 1, title || (first ? first.text : ""), `대표 검색어 \`${keyword}\` 가 제목에도 첫 문단에도 없다. 검색해 들어온 독자가 자기가 친 이름을 못 본다`, null, "error", DOCUMENT, -1),
  ];
}
