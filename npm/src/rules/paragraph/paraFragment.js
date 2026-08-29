// @ts-check
import { PARAGRAPH, finding } from "../finding.js";
import { runsOf } from "../shared/repeat.js";

export const name = "paraFragment";
export const mechanism = "repeat";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const findings = [];
  for (const section of doc.sections) {
    const paragraphs = section.paragraphs;
    // 열쇠는 짧은 문단의 구간 번호다. 코드나 표 뒤의 짧은 문단과 긴 문단 뒤의 짧은 문단은 새 구간을 연다.
    /** @type {string[]} */
    const keys = [];
    let runId = 0;
    let previousShort = false;
    for (const paragraph of paragraphs) {
      const short = paragraph.sentenceCount <= 2;
      if (short) {
        if (!previousShort || !paragraph.followsProseDirectly) runId += 1;
        keys.push(`short${runId}`);
      } else {
        keys.push(`__${paragraph.index}`);
      }
      previousShort = short;
    }
    for (const [start] of runsOf(keys, config.fragmentRun)) {
      const first = paragraphs[start];
      findings.push(
        finding(name, first.startLine, first.sentences.length ? first.sentences[0].text : "", `${config.fragmentRun}개 문단이 연달아 한두 문장씩이다. 화제가 같으면 한 문단으로 묶는다. 줄바꿈은 화제가 바뀌는 자리에만`, null, "error", PARAGRAPH, first.index),
      );
    }
  }
  return findings;
}
