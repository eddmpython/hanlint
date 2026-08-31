// @ts-check
import { DOCUMENT, finding } from "../finding.js";

export const name = "countMismatch";
export const mechanism = "contrast";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc @param {number} line */
function sectionIndexAt(doc, line) {
  let index = 0;
  for (const section of doc.sections) if (section.startLine <= line) index = section.index;
  return index;
}

/** 줄이 든 문단의 차례. sectionIndexAt 과 같은 꼴로 훑는다. */
function blockIndexAt(doc, line) {
  let index = 0;
  for (const block of doc.blocks) if (block.startLine <= line) index = block.index;
  return index;
}

/** 도입의 약속과 마지막 절의 결산만 같은 목록으로 본다. 절이 없으면 첫 문단과 마지막 문단이다. 파이썬과 같다. */
function comparable(doc, lineA, lineB, span) {
  const a = sectionIndexAt(doc, lineA);
  const b = sectionIndexAt(doc, lineB);
  const last = doc.sections[doc.sections.length - 1].index;
  if (last === 0) {
    if (Math.max(...doc.blocks.map((block) => block.endLine)) > span) return false;
    const lastBlock = doc.blocks[doc.blocks.length - 1].index;
    return lastBlock !== 0 && blockIndexAt(doc, lineA) === 0 && blockIndexAt(doc, lineB) === lastBlock;
  }
  return Math.min(a, b) === 0 && Math.max(a, b) === last && a !== b;
}

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const findings = [];
  /** @type {Map<string, [number, number, string][]>} */
  const byUnit = new Map();
  for (const [number, unit, line, text] of doc.countPromises) {
    if (!byUnit.has(unit)) byUnit.set(unit, []);
    /** @type {[number, number, string][]} */ (byUnit.get(unit)).push([line, number, text]);
  }
  for (const promises of byUnit.values()) {
    promises.sort((a, b) => a[0] - b[0] || a[1] - b[1] || (a[2] < b[2] ? -1 : a[2] > b[2] ? 1 : 0));
    for (let i = 0; i < promises.length; i++) {
      const [lineA, numberA, textA] = promises[i];
      const conflict = promises.slice(i + 1).find((p) => p[1] !== numberA && comparable(doc, lineA, p[0], config.countMismatchSpan));
      if (!conflict) continue;
      const [lineB, , textB] = conflict;
      findings.push(finding(name, lineB, textB, `${lineA}번째 줄은 \`${textA}\` 인데 여기는 \`${textB}\` 다. 같은 단위로 다른 수를 약속하면 독자가 어느 쪽을 믿을지 모른다`, null, "error", DOCUMENT, -1));
      break;
    }
  }
  return findings;
}
