// @ts-check
import { overlap, topicsOf } from "../../fingerprint/topics.js";

/** @param {import("../../fingerprint/build.js").SentencePrint} sentence */
export function hasLocalAntecedent(sentence) {
  const marker = sentence.deixis[0];
  const start = sentence.text.indexOf(marker);
  const before = start > 0 ? topicsOf(sentence.text.slice(0, start)) : new Set();
  if (marker.startsWith("이것")) return before.size > 0;
  if (marker.startsWith("해당 ") || marker.startsWith("이러한 ")) return overlap(before, topicsOf(marker)) > 0;
  return false;
}
