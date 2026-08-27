// @ts-check
import { CODE, IMAGE, TABLE } from "../../document/model.js";
import { NOTICE, PARAGRAPH, finding } from "../finding.js";

export const name = "firstResultDistance";
const RESULT_KINDS = [CODE, IMAGE, TABLE];

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const firstResult = doc.blocks.find((b) => RESULT_KINDS.includes(b.kind));
  if (!firstResult) return [];
  const before = doc.paragraphs.filter((p) => p.startLine < firstResult.startLine);
  if (before.length > config.firstResultMaxParagraphs) {
    const over = before[config.firstResultMaxParagraphs];
    return [
      finding(name, over.startLine, over.sentences.length ? over.sentences[0].text : "", `첫 코드나 표까지 산문 문단이 ${before.length}개다. ${config.firstResultMaxParagraphs}개 안에 실행할 것이 온다`, null, NOTICE, PARAGRAPH, over.index),
    ];
  }
  return [];
}
