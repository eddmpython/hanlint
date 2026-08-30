// @ts-check
/** 현재 지적과 지문을 승인 패치의 선택 조건에 맞댄다. */
import { flatSentence, patchFor } from "../data/patches.js";
import { readerKind } from "../fingerprint/readerState.js";
import { sourceSentenceText } from "../fingerprint/sourceSentence.js";
import { SENTENCE, localCue } from "../rules/finding.js";

/**
 * @param {import("../fingerprint/build.js").DocumentPrint | null | undefined} document
 * @param {import("../rules/finding.js").Finding} finding
 * @param {string | null | undefined} preset
 * @param {import("../data/patches.js").Patch[]} patches
 */
export function selectedPatch(document, finding, preset, patches) {
  if (!patches.length || !document || finding.scope !== SENTENCE || finding.at < 0 || finding.at >= document.sentences.length) return undefined;
  const sentence = document.sentences[finding.at];
  const sourceText = sourceSentenceText(document, sentence);
  if (!sourceText) return undefined;
  const state = document.reader.beforeSentence[finding.at];
  return patchFor(finding.rule, preset, sourceText, sentence.text, localCue(finding), readerKind(sentence, state), patches);
}

/**
 * @param {import("../fingerprint/build.js").DocumentPrint | null | undefined} document
 * @param {import("../rules/finding.js").Finding} finding
 * @param {string | null | undefined} preset
 * @param {import("../data/patches.js").Patch[]} patches
 */
export function patchData(document, finding, preset, patches) {
  const patch = selectedPatch(document, finding, preset, patches);
  if (!patch || !preset) return undefined;
  return {
    before: patch.before,
    after: patch.after,
    moved: patch.moved,
    match: {
      sourceText: flatSentence(patch.sourceText),
      sentence: flatSentence(patch.sentence),
      preset,
      cue: patch.cue,
      reader: patch.reader,
    },
  };
}
