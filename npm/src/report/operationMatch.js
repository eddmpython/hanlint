// @ts-check
/** 현재 문장에 승인 표면 치환이 안전하게 하나만 적용되는지 계산한다. */
import { operationData, operationFor } from "../data/operations.js";
import { sourceSentenceTexts } from "../fingerprint/sourceSentence.js";
import { selectedPatch } from "./patchMatch.js";

/**
 * @param {import("../fingerprint/build.js").DocumentPrint | null | undefined} document
 * @param {import("../rules/finding.js").Finding[]} findings
 * @param {string | null | undefined} preset
 * @param {import("../data/operations.js").SurfaceOperation[]} operations
 * @param {import("../data/patches.js").Patch[]} [patches]
 * @param {string[]} [protectedTerms]
 */
export function operationGuidance(document, findings, preset, operations, patches = [], protectedTerms = []) {
  if (!document || !preset || !operations.length) return [];
  const reserved = new Set(findings.filter((finding) => finding.at >= 0 && finding.fix !== null).map((finding) => finding.at));
  for (const finding of findings) {
    if (finding.at >= 0 && selectedPatch(document, finding, preset, patches)) reserved.add(finding.at);
  }
  const sourceTexts = sourceSentenceTexts(document);
  const guidance = [];
  for (const sentence of document.sentences) {
    if (reserved.has(sentence.index)) continue;
    const sourceText = sourceTexts.get(sentence.index);
    if (sourceText === undefined) continue;
    const applied = operationFor(sourceText, preset, operations, protectedTerms);
    if (applied) guidance.push({ line: sentence.line, operation: operationData(applied, preset) });
  }
  return guidance;
}
