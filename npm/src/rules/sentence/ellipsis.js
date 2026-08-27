// @ts-check
import { SENTENCE, finding } from "../finding.js";

export const name = "ellipsis";
// 괄호 안의 점 셋 (`OVER (...)`) 은 인라인 코드의 생략 표기라 뺀다.
const ELLIPSIS = /(?<![(\[])(…|\.{3,})(?![)\]])/;

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const sentence of doc.sentences) {
    if (ELLIPSIS.test(sentence.text)) {
      findings.push(finding(name, sentence.line, sentence.text, "말줄임표로 말끝을 흐리면 독자가 결론을 받아 가지 못한다. 문장을 끝까지 쓴다", null, "error", SENTENCE, sentence.index));
    }
  }
  return findings;
}
