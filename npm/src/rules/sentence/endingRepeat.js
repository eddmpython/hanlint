// @ts-check
import { NOTICE, SENTENCE, finding } from "../finding.js";
import { runsOf } from "../shared/runs.js";

export const name = "endingRepeat";
const COUNTED_ENDINGS = new Set(["니다", "다", "것이다", "요", "죠"]);

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const findings = [];
  for (const section of doc.sections) {
    const sentences = section.paragraphs.flatMap((p) => p.sentences);
    const endings = sentences.map((s) => (COUNTED_ENDINGS.has(s.ending) ? s.ending : `__${s.index}`));
    for (const [start, length, ending] of runsOf(endings, config.endingRun)) {
      const first = sentences[start];
      findings.push(
        finding(name, first.line, first.text, `\`${ending}\` 로 끝나는 문장이 ${length}개 이어진다. 질문, 인과, 행동 동사로 리듬을 바꾼다`, null, NOTICE, SENTENCE, first.index),
      );
    }
  }
  return findings;
}
