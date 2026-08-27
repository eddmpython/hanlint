// @ts-check
import { insideAny } from "../../fingerprint/markers.js";
import { SENTENCE, finding } from "../finding.js";

export const name = "ellipsis";
// 영숫자에 붙은 점 셋 (`v0.0.1...HEAD`, compare URL) 은 범위 표기라 말줄임표가 아니다.
// 인라인 코드와 따옴표 안은 지문이 인용 구간으로 이미 표시해 두었으므로 여기서 다시 재지 않는다.
const ELLIPSIS = /(?<![A-Za-z0-9])(…|\.{3,})(?![A-Za-z0-9])/g;

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const sentence of doc.sentences) {
    const found = [...sentence.text.matchAll(ELLIPSIS)].filter((m) => !insideAny(/** @type {number} */ (m.index), /** @type {number} */ (m.index) + m[0].length, sentence.quoted));
    if (found.length) {
      findings.push(finding(name, sentence.line, sentence.text, "말줄임표로 말끝을 흐리면 독자가 결론을 받아 가지 못한다. 문장을 끝까지 쓴다", null, "error", SENTENCE, sentence.index));
    }
  }
  return findings;
}
