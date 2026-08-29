// @ts-check
import { NOTICE, SENTENCE, finding } from "../finding.js";
import { longSentenceCandidates } from "../shared/candidates.js";

export const name = "longSentence";
export const mechanism = "threshold";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const findings = [];
  for (const sentence of doc.sentences) {
    if (sentence.length > config.longSentenceMax) {
      findings.push(
        finding(name, sentence.line, sentence.text, `어절 ${sentence.length}개다. 상한은 ${config.longSentenceMax}. 마침표로 끊거나 나열이면 목록으로 꺼낸다`, null, NOTICE, SENTENCE, sentence.index, null, null, longSentenceCandidates(sentence.text)),
      );
    }
  }
  return findings;
}
