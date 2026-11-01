// @ts-check
import { topicsOf } from "../../fingerprint/topics.js";
import { DOCUMENT, NOTICE, finding } from "../finding.js";

export const name = "fieldEcho";
export const mechanism = "contrast";

/** 글의 끝으로 보는 절의 수. 결말 뒤에 `더 해 볼 것` 목록이 붙는 경우가 흔하다. 파이썬과 같다. */
const ENDING_SECTIONS = 2;

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../fingerprint/build.js").SectionPrint[]} sections
 * @param {string[]} fields
 * @param {string} where
 */
function check(doc, sections, fields, where) {
  const findings = [];
  const section = sections[0];
  for (const name_ of fields) {
    const value = doc.frontmatter[name_];
    if (!value) continue;
    const promised = topicsOf(value);
    if (!promised.size) continue;
    if ([...promised].some((word) => sections.some((spoken) => spoken.topics.has(word)))) continue;
    findings.push(
      finding(name, section.startLine, value, `frontmatter의 \`${name_}\` 필드가 약속한 말이 ${where}에 하나도 없다. 약속한 것을 ${where}에서 그 말로 답한다`, null, NOTICE, DOCUMENT, section.index),
    );
  }
  return findings;
}

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  if (!config.introFields.length && !config.endingFields.length) return [];
  const findings = check(doc, [doc.intro], config.introFields, "도입");
  if (doc.sections.length > 1) findings.push(...check(doc, doc.sections.slice(-ENDING_SECTIONS), config.endingFields, "글의 끝"));
  return findings;
}
