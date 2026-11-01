// @ts-check
import { SENTENCE, finding } from "../finding.js";

export const name = "imperativePeriod";
export const mechanism = "dictionary";
const IMPERATIVE_PERIOD = /(세요|십시오|합시다|봅시다|하자|해라|라)\.(?=\s|$)/;

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const sentence of doc.sentences) {
    const match = IMPERATIVE_PERIOD.exec(sentence.text);
    if (!match) continue;
    const start = /** @type {number} */ (match.index);
    const fix = sentence.text.slice(0, start) + match[1] + sentence.text.slice(start + match[0].length);
    findings.push(
      finding(name, sentence.line, sentence.text, `명령·청유 문장 끝(\`${match[1]}\`)에 마침표를 붙이지 않는 표기 방침이다`, fix, "error", SENTENCE, sentence.index, match[0], match[1]),
    );
  }
  return findings;
}
