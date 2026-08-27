// @ts-check
import { SENTENCE, finding } from "../finding.js";

export const name = "doublePassive";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const sentence of doc.sentences) {
    if (sentence.passives.length) {
      findings.push(
        finding(name, sentence.line, sentence.text, `\`${sentence.passives[0]}\` 는 피동에 어지다 를 또 붙인 이중 피동이다. 하나만 남긴다`, null, "error", SENTENCE, sentence.index),
      );
    }
  }
  return findings;
}
