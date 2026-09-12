// @ts-check
/** Python learn/operations.py의 표면 치환 후보와 증거 묶음. */
import { operationFromApproval } from "../data/operations.js";
import { sourceSentenceTexts } from "../fingerprint/sourceSentence.js";
import { changedSentencePairs } from "./pairs.js";

export function learnOperations(beforeDoc, afterDoc, preset = null, protectedTerms = []) {
  const pairs = changedSentencePairs(beforeDoc.sentences, afterDoc.sentences);
  const rawBefore = sourceSentenceTexts(beforeDoc), rawAfter = sourceSentenceTexts(afterDoc);
  const beforeByIndex = new Map(beforeDoc.sentences.map((item) => [item.index, item]));
  const grouped = new Map(), presets = preset ? [preset] : [];
  for (const [index, after] of pairs) {
    const before = beforeByIndex.get(index);
    if (after.length !== 1 || !before) continue;
    const sourceBefore = (rawBefore.get(index) ?? before.text).trim();
    const sourceAfter = (rawAfter.get(after[0].index) ?? after[0].text).trim();
    const operation = operationFromApproval(sourceBefore, sourceAfter, presets, protectedTerms);
    if (!operation) continue;
    const key = JSON.stringify([operation.before, operation.after]);
    const item = grouped.get(key) ?? { kind: "surfaceSubstitution", before: operation.before, after: operation.after, evidence: [] };
    item.evidence.push({ sourceBefore, sourceAfter, beforeLine: before.line, afterLine: after[0].line });
    grouped.set(key, item);
  }
  return [...grouped.values()].map((item) => ({ ...item, evidenceCount: item.evidence.length,
    guards: { maximumCharacters: 32, maximumSurfaceEditDistance: 1, protectedFacts: true, uniqueWordBoundary: true },
    ...(preset ? { presets } : {}),
  }));
}
