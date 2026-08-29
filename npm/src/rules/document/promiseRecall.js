// @ts-check
import { DOCUMENT, NOTICE, finding } from "../finding.js";

export const name = "promiseRecall";
export const mechanism = "reader";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const reader = doc.reader.final;
  if (!reader.promises.length || reader.recalls.length) return [];
  return reader.promises.map(([line, text]) =>
    finding(name, line, text, "뒤로 미룬 것을 앞에서 미룬 것으로 다시 부르는 자리가 글 어디에도 없다. 회수하거나 미루지 않는다", null, NOTICE, DOCUMENT, -1),
  );
}
