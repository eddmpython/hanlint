// @ts-check
import { matchedTexts } from "../../fingerprint/markers.js";
import { DOCUMENT, finding } from "../finding.js";

export const name = "bridgeRepeat";

/**
 * 절을 닫는 문장이 이음 표지 (이번에는, 이제, 다음으로) 로 시작하는 절이 bridgeRepeatMin 개 이상인 글.
 * 파이썬 rules/structure/bridgeRepeat.py 와 같다. 표지 목록은 data/bridgeOpeners.txt.
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  /** @type {[import("../../fingerprint/build.js").SentencePrint, string][]} */
  const closers = [];
  for (const section of doc.bodySections) {
    if (!section.paragraphs.length) continue;
    const sentences = section.paragraphs[section.paragraphs.length - 1].sentences;
    if (!sentences.length) continue;
    const last = sentences[sentences.length - 1];
    const found = matchedTexts(last.text, "bridgeOpeners.txt");
    if (found.length) closers.push([last, found[0]]);
  }
  if (closers.length < config.bridgeRepeatMin) return [];
  const markers = [...new Set(closers.map(([, marker]) => marker))].sort();
  const [first] = closers[0];
  return [
    finding(
      name,
      first.line,
      first.text,
      `절 ${closers.length}개가 \`${markers.join(", ")}\` 같은 이음 표지로 시작하는 문장으로 닫힌다. 예고가 절마다 되풀이되면 틀이다. 방금 만든 결과를 이름으로 부르고 아직 못 하는 일을 적는다`,
      null,
      "error",
      DOCUMENT,
      -1,
    ),
  ];
}
