// @ts-check
import { DOCUMENT, NOTICE, finding } from "../finding.js";

export const name = "promiseRecall";
export const mechanism = "reader";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const reader = doc.reader.final;
  if (!reader.promises.length || reader.recalls.length) return [];
  return reader.promises.map(([line, text]) =>
    finding(name, line, text, "뒤로 미룬 이야기를 `앞에서 미룬 X`처럼 다시 부르는 문장이 글 어디에도 없다. 뒤에서 다루거나 처음부터 미루지 않는다", null, NOTICE, DOCUMENT, -1),
  );
}
