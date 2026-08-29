// @ts-check
import { topicsOf } from "../../fingerprint/topics.js";
import { DOCUMENT, NOTICE, finding } from "../finding.js";

export const name = "fieldEcho";
export const mechanism = "contrast";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../fingerprint/build.js").SectionPrint} section
 * @param {string[]} fields
 * @param {string} where
 */
function check(doc, section, fields, where) {
  const findings = [];
  for (const name_ of fields) {
    const value = doc.frontmatter[name_];
    if (!value) continue;
    const promised = topicsOf(value);
    if (!promised.size) continue;
    if ([...promised].some((word) => section.topics.has(word))) continue;
    findings.push(
      finding(name, section.startLine, value, `frontmatter 의 \`${name_}\` 가 약속한 말이 ${where}에 하나도 없다. 약속한 것을 ${where}에서 그 말로 답한다`, null, NOTICE, DOCUMENT, section.index),
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
  const findings = check(doc, doc.intro, config.introFields, "도입");
  if (doc.sections.length > 1) findings.push(...check(doc, doc.sections[doc.sections.length - 1], config.endingFields, "마지막 절"));
  return findings;
}
