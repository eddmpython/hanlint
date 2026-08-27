// @ts-check
import { LIST, PROSE } from "../../document/model.js";
import { SECTION, finding } from "../finding.js";

export const name = "sectionNoProse";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const section of doc.bodySections) {
    const kinds = new Set(section.blockKinds);
    if (!kinds.size || kinds.has(PROSE) || kinds.has(LIST)) continue;
    findings.push(finding(name, section.startLine, section.title, "설명글 없이 코드, 표, 이미지만 있는 절이다. 절은 제목과 시각 자료와 설명글로 짠다", null, "error", SECTION, section.index));
  }
  return findings;
}
