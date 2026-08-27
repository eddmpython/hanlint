// @ts-check
import { insideAny, matchedSpans } from "../../fingerprint/markers.js";
import { SENTENCE, finding } from "../finding.js";

export const name = "draftHistory";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  void config;
  const findings = [];
  for (const sentence of doc.sentences) {
    for (const [start, end, text] of matchedSpans(sentence.text, "draftHistory.txt")) {
      if (insideAny(start, end, sentence.quoted)) continue;
      findings.push(
        finding(name, sentence.line, sentence.text, `\`${text}\` 는 글쓴이의 과정이다. 독자는 초고를 본 적이 없다. 알아낸 사실만 결과 문장으로 남긴다`, null, "error", SENTENCE, sentence.index),
      );
    }
  }
  return findings;
}
