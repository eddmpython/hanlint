// @ts-check
import { fitJosa } from "../../analysis/grammar/josa.js";
import { overlap } from "../../fingerprint/topics.js";
import { SENTENCE, finding } from "../finding.js";
import { hasLocalAntecedent } from "../shared/localAntecedent.js";

export const name = "deixis";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const sentence of doc.sentences) {
    if (!sentence.deixis.length || sentence.index === 0) continue;
    if (hasLocalAntecedent(sentence)) continue;
    const previous = doc.sentences[sentence.index - 1];
    if (overlap(previous.topics, sentence.topics) === 0) continue;
    findings.push(
      finding(name, sentence.line, sentence.text, `\`${sentence.deixis[0]}\` ${fitJosa(sentence.deixis[0], "은")} 독자가 스크롤을 되돌려야 하는 지시어다. 가리키는 파일, 값, 코드의 이름을 쓴다`, null, "error", SENTENCE, sentence.index),
    );
  }
  return findings;
}
