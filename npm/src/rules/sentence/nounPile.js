// @ts-check
import { SENTENCE, finding } from "../finding.js";

export const name = "nounPile";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const findings = [];
  for (const sentence of doc.sentences) {
    if (sentence.nounRun >= config.nounPileMin) {
      findings.push(
        finding(name, sentence.line, sentence.text, `명사 ${sentence.nounRun}개가 조사 없이 이어진다. 관계가 표시되지 않아 독자가 조사를 끼워 넣는다. 동사로 되돌린다`, null, "error", SENTENCE, sentence.index),
      );
    }
  }
  return findings;
}
