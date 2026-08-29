// @ts-check
import { SENTENCE, finding } from "../finding.js";
import { runsOf } from "../shared/repeat.js";

export const name = "connectorRepeat";
export const mechanism = "repeat";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const paragraph of doc.paragraphs) {
    const sentences = paragraph.sentences;
    // 열쇠는 문두 접속부사다. 접속부사가 없는 문장은 저마다 다른 열쇠를 받아 구간을 끊는다.
    const keys = sentences.map((sentence) => sentence.connectorStart || `__${sentence.index}`);
    for (const [start, length, connector] of runsOf(keys, 2)) {
      for (const sentence of sentences.slice(start + 1, start + length)) {
        findings.push(
          finding(name, sentence.line, sentence.text, `\`${connector}\` 로 시작하는 문장이 연달아 온다. 앞에서 만든 것의 이름을 불러 잇는다`, null, "error", SENTENCE, sentence.index),
        );
      }
    }
  }
  return findings;
}
