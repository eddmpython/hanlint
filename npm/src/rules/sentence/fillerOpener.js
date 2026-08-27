// @ts-check
import { SENTENCE, finding } from "../finding.js";

export const name = "fillerOpener";
const FILLER = /^(다음으로|이어서|마지막에는|마지막으로)(?=[\s,])/;

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const sentence of doc.sentences) {
    const match = FILLER.exec(sentence.text);
    if (!match) continue;
    findings.push(
      finding(name, sentence.line, sentence.text, `\`${match[1]}\` 만 붙여 잇는 문장이다. 앞에서 만든 파일이나 값을 이름으로 다시 부르고 다음 행동을 붙인다`, null, "error", SENTENCE, sentence.index),
    );
  }
  return findings;
}
