// @ts-check
import { SENTENCE, finding } from "../finding.js";

export const name = "imperativePeriod";
const IMPERATIVE_PERIOD = /(세요|십시오|합시다|봅시다|하자|해라)\.(?=\s|$)/;

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const sentence of doc.sentences) {
    const match = IMPERATIVE_PERIOD.exec(sentence.text);
    if (!match) continue;
    const start = /** @type {number} */ (match.index);
    const fix = sentence.text.slice(0, start) + match[1] + sentence.text.slice(start + match[0].length);
    findings.push(finding(name, sentence.line, sentence.text, `\`${match[1]}\` 처럼 명령형과 청유형 뒤에는 마침표를 붙이지 않는다`, fix, "error", SENTENCE, sentence.index));
  }
  return findings;
}
