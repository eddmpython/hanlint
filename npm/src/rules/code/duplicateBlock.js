// @ts-check
import { DOCUMENT, NOTICE, finding } from "../finding.js";
import { codeBlocksOf } from "../shared/codeBlocks.js";

export const name = "duplicateBlock";
export const mechanism = "repeat";
const MIN_LINES = 4;

/** 줄 다중집합의 겹침 비. 2 * 공통 / (a + b). @param {string[]} a @param {string[]} b */
function similarity(a, b) {
  if (!a.length || !b.length) return 0;
  /** @type {Map<string, number>} */
  const counts = new Map();
  for (const line of a) counts.set(line, (counts.get(line) ?? 0) + 1);
  let common = 0;
  for (const line of b) {
    const n = counts.get(line) ?? 0;
    if (n > 0) {
      counts.set(line, n - 1);
      common += 1;
    }
  }
  return (2 * common) / (a.length + b.length);
}

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const findings = [];
  const blocks = codeBlocksOf(doc).filter((b) => b.lines.filter(([, line]) => line.trim()).length >= MIN_LINES);
  for (let later = 0; later < blocks.length; later++) {
    const current = blocks[later];
    const currentLines = current.lines.filter(([, line]) => line.trim()).map(([, line]) => line.trim());
    for (let earlier = 0; earlier < later; earlier++) {
      const previous = blocks[earlier];
      if (previous.isOutput !== current.isOutput) continue;
      const ratio = similarity(previous.lines.filter(([, line]) => line.trim()).map(([, line]) => line.trim()), currentLines);
      if (ratio >= config.duplicateBlockRatio) {
        findings.push(
          finding(name, current.startLine, currentLines[0], `${previous.startLine}번째 줄의 블록과 ${Math.round(ratio * 100)}% 같다. 다른 줄만 남기거나 앞 블록을 가리킨다`, null, NOTICE, DOCUMENT, current.index),
        );
        break;
      }
    }
  }
  return findings;
}
