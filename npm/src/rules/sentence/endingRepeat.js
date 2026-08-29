// @ts-check
import { NOTICE, SENTENCE, finding } from "../finding.js";
import { runsOf } from "../shared/runs.js";

export const name = "endingRepeat";
export const mechanism = "repeat";
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
      // 구간 어딘가에 이유를 잇는 말이나 독자를 부르는 말이 있으면 리듬이 산 것이다. 구간을 쪼개면
      // 조각마다 지적이 되어 오히려 늘어난다. 구간 전체를 하나로 보고 살린다.
      if (sentences.slice(start, start + length).some((s) => s.causal || s.readerCall)) continue;
      const first = sentences[start];
      findings.push(
        finding(name, first.line, first.text, `\`${ending}\` 로 끝나는 문장 ${length}개에 인과도 질문도 독자를 부르는 말도 없다. 질문, 인과, 행동 동사로 리듬을 바꾼다`, null, NOTICE, SENTENCE, first.index),
      );
    }
  }
  return findings;
}
