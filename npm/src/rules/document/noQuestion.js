// @ts-check
import { DOCUMENT, finding } from "../finding.js";

export const name = "noQuestion";
export const mechanism = "threshold";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc, config) {
  if (doc.bodySections.length < 2 || doc.questionCount > 0) return [];
  const first = doc.sentences.length ? doc.sentences[0] : null;
  const why = doc.readerCallCount === 0
    ? "물음표가 한 번도 없고 독자에게 말을 거는 문장도 없다. 질문이나 독자에게 말을 거는 문장이 필요한 글인지 판단하고, 설명만으로 충분하면 그대로 둔다"
    : "물음표가 한 번도 없다. 질문이 필요한 글인지 판단하고, 설명만으로 충분하면 그대로 둔다";
  return [finding(name, first ? first.line : 1, first ? first.text : "", why, null, config.enforceStyle.includes(name) ? "error" : "notice", DOCUMENT, -1)];
}
