// @ts-check
import { DOCUMENT, finding } from "../finding.js";

export const name = "headingSentence";
const SENTENCE_ENDINGS = ["니다", "한다", "해요", "세요", "십시오", "합시다", "."];

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const findings = [];
  for (const [level, text, line] of doc.headings) {
    if (level > config.headingSentenceMaxLevel) continue;
    const trimmed = text.trimEnd();
    if (SENTENCE_ENDINGS.some((ending) => trimmed.endsWith(ending))) {
      findings.push(finding(name, line, text, "절 제목이 본문 문장을 복사했다. 대상이나 질문을 짧게 쓴다", null, "error", DOCUMENT, -1));
    }
  }
  return findings;
}
