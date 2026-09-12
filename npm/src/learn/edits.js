// @ts-check
/** Python learn/edits.py와 같은 원문 문장 대응 및 지적 소멸 후보다. */
import { sourceSentenceTexts } from "../fingerprint/sourceSentence.js";
import { readerKind } from "../fingerprint/readerState.js";
import { localCue, SENTENCE } from "../rules/finding.js";
import { changedSentencePairs } from "./pairs.js";

export function learnExemplars(beforeDoc, afterDoc, beforeFindings, afterFindings, preset = null) {
  const pairs = changedSentencePairs(beforeDoc.sentences, afterDoc.sentences);
  const rawBefore = sourceSentenceTexts(beforeDoc), rawAfter = sourceSentenceTexts(afterDoc);
  const remaining = new Set(afterFindings.filter((item) => item.scope === SENTENCE && item.at >= 0).map((item) => `${item.rule}:${item.at}`));
  const beforeByIndex = new Map(beforeDoc.sentences.map((item) => [item.index, item]));
  const seen = new Set(), learned = [];
  for (const finding of beforeFindings) {
    const key = `${finding.rule}:${finding.at}`;
    if (finding.scope !== SENTENCE || finding.at < 0 || seen.has(key)) continue;
    const after = pairs.get(finding.at), before = beforeByIndex.get(finding.at);
    if (!after || !before || after.some((item) => remaining.has(`${finding.rule}:${item.index}`))) continue;
    const afterPlain = after.map((item) => item.text.trim()).filter(Boolean).join(" ");
    const afterText = after.filter((item) => item.text.trim()).map((item) => (rawAfter.get(item.index) ?? item.text).trim()).join(" ");
    if (!afterText || before.text.trim() === afterPlain) continue;
    seen.add(key);
    learned.push({ rule: finding.rule, before: (rawBefore.get(before.index) ?? before.text).trim(), after: afterText,
      moved: "실제 수정본의 문장으로 바꿈", why: finding.why, beforeLine: before.line,
      afterLines: [...new Set(after.map((item) => item.line))], sentence: before.text.trim(),
      cue: localCue(finding), reader: readerKind(before, beforeDoc.reader.beforeSentence[finding.at]),
      ...(preset ? { presets: [preset] } : {}),
    });
  }
  return learned;
}
