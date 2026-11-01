// @ts-check
/** 독자가 막힐 곳. 새로 판정하지 않고, reader 방법을 쓰는 규칙의 지적을 사람이 읽을 이름으로 묶는다. */

import { ruleMechanism } from "./registry.js";

/** @param {import("./finding.js").Finding[]} findings */
export function readerDebts(findings) {
  return findings.filter((finding) => ruleMechanism(finding.rule) === "reader");
}
