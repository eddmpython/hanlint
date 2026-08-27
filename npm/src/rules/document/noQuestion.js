// @ts-check
import { DOCUMENT, finding } from "../finding.js";

export const name = "noQuestion";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  if (doc.bodySections.length < 2 || doc.questionCount > 0) return [];
  const first = doc.sentences.length ? doc.sentences[0] : null;
  return [finding(name, first ? first.line : 1, first ? first.text : "", "물음표가 한 번도 없다. 독자가 품을 의문을 한 번은 대신 묻고 다음 문장에서 답한다", null, "error", DOCUMENT, -1)];
}
