// @ts-check
import { PARAGRAPH, finding } from "../finding.js";

export const name = "introLong";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  if (!doc.bodySections.length) return [];
  const paragraphs = doc.intro.paragraphs;
  if (paragraphs.length > config.introMaxParagraphs) {
    const over = paragraphs[config.introMaxParagraphs];
    return [
      finding(name, over.startLine, over.sentences.length ? over.sentences[0].text : "", `도입 산문 문단이 ${paragraphs.length}개다. ${config.introMaxParagraphs}개를 넘지 않는다. 첫 코드 블록이 그 안에 온다`, null, "error", PARAGRAPH, over.index),
    ];
  }
  return [];
}
