// @ts-check
import { LIST } from "../../document/model.js";
import { DOCUMENT, finding } from "../finding.js";

export const name = "emojiBullet";
// 이모지 범위. 코드포인트로 만든다 (도구가 이스케이프를 건드리지 않게). 아스트랄 범위라 u 플래그가 필요하다.
const EMOJI =
  "[" +
  String.fromCodePoint(0x1f300) +
  "-" +
  String.fromCodePoint(0x1faff) +
  String.fromCodePoint(0x2600) +
  "-" +
  String.fromCodePoint(0x27bf) +
  String.fromCodePoint(0x2b50) +
  String.fromCodePoint(0x2b06) +
  "]";
const BULLET_WITH_EMOJI = new RegExp(/^\s*(?:[-*+]|\d+[.)])\s+/.source + EMOJI, "u");

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const block of doc.blocks) {
    if (block.kind !== LIST) continue;
    const lines = block.text.split("\n");
    for (let offset = 0; offset < lines.length; offset++) {
      if (BULLET_WITH_EMOJI.test(lines[offset])) {
        findings.push(finding(name, block.startLine + offset, lines[offset].trim(), "목록 항목이 이모지로 시작한다. 이모지를 지우고 첫 낱말이 내용을 말하게 한다", null, "error", DOCUMENT, block.index));
        break;
      }
    }
  }
  return findings;
}
