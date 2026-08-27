// @ts-check
import { NOTICE, PARAGRAPH, finding } from "../finding.js";

export const name = "factListParagraph";

/** 문장 사이를 잇는 표지가 하나라도 있는가. @param {import("../../fingerprint/build.js").ParagraphPrint} paragraph */
function isLinked(paragraph) {
  if (paragraph.causalTotal > 0) return true;
  return paragraph.sentences.some((s) => s.connectorStart || s.mood === "의문" || s.readerCall);
}

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const findings = [];
  for (const paragraph of doc.paragraphs) {
    if (paragraph.sentenceCount < config.factListMinSentences || isLinked(paragraph)) continue;
    if (paragraph.meanLength <= config.factListMaxMeanLength) {
      findings.push(
        finding(name, paragraph.startLine, paragraph.sentences[0].text, `문장 ${paragraph.sentenceCount}개에 인과 표지가 하나도 없다. 사실만 나열한 문단일 수 있다. 그래서, 때문에 로 잇는다`, null, NOTICE, PARAGRAPH, paragraph.index),
      );
    }
  }
  return findings;
}
