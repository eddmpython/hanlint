// @ts-check
import { NOTICE, PARAGRAPH, finding } from "../finding.js";

export const name = "topicBreak";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const findings = [];
  for (const section of doc.sections) {
    const paragraphs = section.paragraphs;
    for (let i = 0; i + 1 < paragraphs.length; i++) {
      const previous = paragraphs[i];
      const paragraph = paragraphs[i + 1];
      if (paragraph.overlapWithPrevious !== 0) continue;
      if (Math.min(previous.sentenceCount, paragraph.sentenceCount) < config.topicBreakMinSentences) continue;
      findings.push(
        finding(name, paragraph.startLine, paragraph.sentences[0].text, "앞 문단과 화제어가 하나도 겹치지 않는다. 앞에서 만든 것의 이름을 첫 문장에서 다시 부른다", null, NOTICE, PARAGRAPH, paragraph.index),
      );
    }
  }
  return findings;
}
