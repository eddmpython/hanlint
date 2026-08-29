// @ts-check
import { DOCUMENT, finding } from "../finding.js";

export const name = "headingQuestion";
export const mechanism = "repeat";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const headings = doc.headings.filter(([level]) => level === 2);
  if (headings.length < 3) return [];
  const asking = headings.filter(([, text]) => text.trimEnd().endsWith("?")).map(([, text]) => text);
  if (asking.length / headings.length <= config.headingQuestionRatio) return [];
  return [
    finding(name, headings[0][2], asking.join(" / "), `H2 ${headings.length}개 중 ${asking.length}개가 물음표로 끝난다. 목차가 과정이 아니라 FAQ 로 읽힌다. 형태를 섞는다`, null, "error", DOCUMENT, -1),
  ];
}
