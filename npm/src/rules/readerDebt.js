// @ts-check
/** 독자 부채는 새 판정이 아니라 reader 기제 Finding을 사람이 읽는 이름으로 묶은 것이다. */

import { ruleMechanism } from "./registry.js";

/** @param {import("./finding.js").Finding[]} findings */
export function readerDebts(findings) {
  return findings.filter((finding) => ruleMechanism(finding.rule) === "reader");
}
