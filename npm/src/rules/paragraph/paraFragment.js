// @ts-check
import { PARAGRAPH, finding } from "../finding.js";

export const name = "paraFragment";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const findings = [];
  for (const section of doc.sections) {
    /** @type {import("../../fingerprint/build.js").ParagraphPrint[]} */
    let run = [];
    for (const paragraph of section.paragraphs) {
      const short = paragraph.sentenceCount <= 2;
      if (short && (!run.length || paragraph.followsProseDirectly)) run.push(paragraph);
      else if (short) run = [paragraph];
      else run = [];
      if (run.length === config.fragmentRun) {
        const first = run[0];
        findings.push(
          finding(name, first.startLine, first.sentences.length ? first.sentences[0].text : "", `${run.length}개 문단이 연달아 한두 문장씩이다. 화제가 같으면 한 문단으로 묶는다. 줄바꿈은 화제가 바뀌는 자리에만`, null, "error", PARAGRAPH, first.index),
        );
      }
    }
  }
  return findings;
}
