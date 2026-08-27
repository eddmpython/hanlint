// @ts-check
import { DOCUMENT, finding } from "../finding.js";

export const name = "dash";
// 리터럴로 쓰면 이 파일이 자기 게이트에 걸린다. 코드포인트로 만든다.
const DASHES = new RegExp(`[${String.fromCharCode(0x2013)}${String.fromCharCode(0x2014)}]`);

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const block of doc.blocks) {
    block.text.split("\n").forEach((lineText, offset) => {
      if (DASHES.test(lineText)) {
        findings.push(
          finding(name, block.startLine + offset, lineText.trim(), "긴 줄표다. 부연은 마침표로 끊거나 괄호로, 범위는 물결표 ~ 로 쓴다", null, "error", DOCUMENT, block.index),
        );
      }
    });
  }
  return findings;
}
