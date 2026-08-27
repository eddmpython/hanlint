// @ts-check
import { DOCUMENT, NOTICE, finding } from "../finding.js";

export const name = "readerAbsent";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  if (doc.bodySections.length < 2 || doc.questionCount > 0 || doc.readerCallCount > 0) return [];
  const first = doc.sentences.length ? doc.sentences[0] : null;
  return [finding(name, first ? first.line : 1, first ? first.text : "", "질문도 독자를 부르는 문장도 없다. 독자가 할 행동을 동사로 끝내는 문장을 한 번은 넣는다", null, NOTICE, DOCUMENT, -1)];
}
