// @ts-check
import { fitJosa } from "../../analysis/grammar/josa.js";
import { matchedTexts } from "../../fingerprint/markers.js";
import { SENTENCE, finding } from "../finding.js";

export const name = "enoughOnce";
export const mechanism = "repeat";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  void config;
  /** @type {[import("../../fingerprint/build.js").SentencePrint, string][]} */
  const breaks = [];
  for (const sentence of doc.sentences) {
    const texts = matchedTexts(sentence.text, "enoughMarkers.txt");
    if (texts.length) breaks.push([sentence, texts[0]]);
  }
  if (breaks.length < 2) return [];
  const first = breaks[0][0];
  return breaks.slice(1).map(([sentence, text]) =>
    finding(name, sentence.line, sentence.text, `\`${text}\`${fitJosa(text, "로")} 끊는 문장이 ${first.line}번째 줄에 이미 있다. 글 전체에 한 번만 쓴다. 여러 번 쓰면 끝난다고 해 놓고 글이 계속 이어진다`, null, "error", SENTENCE, sentence.index),
  );
}
