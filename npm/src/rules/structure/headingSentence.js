// @ts-check
import { DOCUMENT, finding } from "../finding.js";

export const name = "headingSentence";
const SENTENCE_ENDINGS = ["니다", "세요", "십시오", "합시다", "."];

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const [, text, line] of doc.headings) {
    const trimmed = text.trimEnd();
    if (SENTENCE_ENDINGS.some((ending) => trimmed.endsWith(ending))) {
      findings.push(finding(name, line, text, "절 제목이 본문 문장을 복사했다. 대상이나 질문을 짧게 쓴다", null, "error", DOCUMENT, -1));
    }
  }
  return findings;
}
