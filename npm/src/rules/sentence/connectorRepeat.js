// @ts-check
import { SENTENCE, finding } from "../finding.js";

export const name = "connectorRepeat";
export const mechanism = "repeat";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const paragraph of doc.paragraphs) {
    /** @type {string | null} */
    let previous = null;
    for (const sentence of paragraph.sentences) {
      const current = sentence.connectorStart;
      if (current && current === previous) {
        findings.push(
          finding(name, sentence.line, sentence.text, `\`${current}\` 로 시작하는 문장이 연달아 온다. 앞에서 만든 것의 이름을 불러 잇는다`, null, "error", SENTENCE, sentence.index),
        );
      }
      previous = current;
    }
  }
  return findings;
}
