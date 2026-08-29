// @ts-check
import { euiAdjacent } from "../../analysis/index.js";
import { SENTENCE, finding } from "../finding.js";

export const name = "euiChain";
export const mechanism = "threshold";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const sentence of doc.sentences) {
    if (sentence.euiCount >= 3 || (sentence.euiCount >= 2 && euiAdjacent(sentence.text))) {
      findings.push(
        finding(name, sentence.line, sentence.text, `한 문장에 \`의\` 가 ${sentence.euiCount}번이다. 명사를 쌓은 자리라 관계가 표시되지 않는다. 동사로 편다`, null, "error", SENTENCE, sentence.index),
      );
    }
  }
  return findings;
}
