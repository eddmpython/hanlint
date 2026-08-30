// @ts-check
import { SENTENCE, finding } from "../finding.js";
import { doublePassiveCandidates } from "../shared/candidates.js";

export const name = "doublePassive";
export const mechanism = "dictionary";

/** 검토를 통과한 이중 피동 후보에서 인용 밖의 단일 치환만 꺼낸다.
 * @param {string} text @param {string} candidateText @param {[number, number][]} quoted
 * @returns {[string, string] | null} */
function approvedEdit(text, candidateText, quoted) {
  let prefix = 0;
  while (prefix < text.length && prefix < candidateText.length && text[prefix] === candidateText[prefix]) prefix += 1;
  let suffix = 0;
  while (
    suffix < text.length - prefix &&
    suffix < candidateText.length - prefix &&
    text[text.length - suffix - 1] === candidateText[candidateText.length - suffix - 1]
  ) suffix += 1;
  const sourceEnd = text.length - suffix;
  const candidateEnd = candidateText.length - suffix;
  const fragment = text.slice(prefix, sourceEnd);
  const replacement = candidateText.slice(prefix, candidateEnd);
  if (!fragment || text.indexOf(fragment) !== text.lastIndexOf(fragment)) return null;
  if (quoted.some(([start, end]) => prefix < end && sourceEnd > start)) return null;
  return [fragment, replacement];
}

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const sentence of doc.sentences) {
    if (sentence.passives.length) {
      const candidates = doublePassiveCandidates(sentence.text, sentence.passives);
      const approved = candidates.length === 1 ? approvedEdit(sentence.text, candidates[0].text, sentence.quoted) : null;
      findings.push(
        finding(
          name,
          sentence.line,
          sentence.text,
          `\`${sentence.passives[0]}\` 는 피동에 어지다 를 또 붙인 이중 피동이다. 하나만 남긴다`,
          approved ? candidates[0].text : null,
          "error",
          SENTENCE,
          sentence.index,
          approved ? approved[0] : null,
          approved ? approved[1] : null,
          approved ? [] : candidates,
        ),
      );
    }
  }
  return findings;
}
