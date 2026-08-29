// @ts-check
import { LIST } from "../../document/model.js";
import { plainText } from "../../document/plainText.js";
import { NOTICE, SECTION, finding } from "../finding.js";

export const name = "moreLater";
export const mechanism = "threshold";
const BULLET = /^\s*(?:[-*+]|\d+[.)])\s+/;

/** (블록 안 줄 오프셋, 항목 전체). 이어지는 줄은 앞 항목에 붙인다. @param {string} text @returns {[number, string][]} */
function itemsOf(text) {
  /** @type {[number, string][]} */
  const items = [];
  text.split("\n").forEach((line, offset) => {
    if (BULLET.test(line)) {
      items.push([offset, line.replace(BULLET, "").trim()]);
    } else if (items.length && line.trim()) {
      const last = items[items.length - 1];
      last[1] = `${last[1]} ${line.trim()}`;
    }
  });
  return items;
}

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  if (doc.sections.length < 2) return [];
  const last = doc.sections[doc.sections.length - 1];
  if (last.isIntro) return [];
  /** @type {[number, string][]} */
  const over = [];
  for (const block of doc.blocks) {
    if (block.kind !== LIST || block.startLine < last.startLine) continue;
    for (const [offset, item] of itemsOf(block.text)) {
      const visible = plainText(item);
      if (visible.length > config.moreLaterMaxChars) over.push([block.startLine + offset, visible]);
    }
  }
  if (!over.length) return [];
  let best = over[0];
  for (const pair of over) if (pair[1].length > best[1].length) best = pair;
  return [
    finding(name, best[0], best[1], `마지막 절의 목록 항목 ${over.length}개가 ${config.moreLaterMaxChars}자를 넘는다 (가장 긴 것 ${best[1].length}자). 미룬 것이 아니라 옮겨 적은 것이다. 한 줄과 링크로 줄인다`, null, NOTICE, SECTION, last.index),
  ];
}
