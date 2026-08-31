// @ts-check
import { PARAGRAPH, finding } from "../finding.js";

export const name = "introLong";
export const mechanism = "threshold";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  // 본문 절이 하나뿐이거나 도입이 문단의 절반을 넘으면 절이 없는 글이지 도입이 긴 글이 아니다. 파이썬과 같다.
  if (doc.bodySections.length < 2) return [];
  const paragraphs = doc.intro.paragraphs;
  if (paragraphs.length * 2 > doc.paragraphs.length) return [];
  if (paragraphs.length > config.introMaxParagraphs) {
    const over = paragraphs[config.introMaxParagraphs];
    return [
      finding(name, over.startLine, over.sentences.length ? over.sentences[0].text : "", `도입 산문 문단이 ${paragraphs.length}개다. ${config.introMaxParagraphs}개를 넘지 않는다. 첫 코드 블록이 그 안에 온다`, null, "error", PARAGRAPH, over.index),
    ];
  }
  return [];
}
