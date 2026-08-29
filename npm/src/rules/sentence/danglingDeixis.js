// @ts-check
import { fitJosa } from "../../analysis/grammar/josa.js";
import { overlap } from "../../fingerprint/topics.js";
import { SENTENCE, finding } from "../finding.js";
import { danglingDeixisCandidates } from "../shared/candidates.js";
import { hasLocalAntecedent } from "../shared/localAntecedent.js";

export const name = "danglingDeixis";
export const mechanism = "reader";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const sentence of doc.sentences) {
    if (!sentence.deixis.length) continue;
    if (hasLocalAntecedent(sentence)) continue;
    const reader = doc.reader.beforeSentence[sentence.index];
    if (overlap(reader.recent, sentence.topics) > 0) continue;
    findings.push(
      finding(name, sentence.line, sentence.text, `\`${sentence.deixis[0]}\` ${fitJosa(sentence.deixis[0], "이")} 가리킬 것이 앞 문장에 없다. 가리키는 파일, 값, 코드의 이름을 쓴다`, null, "error", SENTENCE, sentence.index, null, null, danglingDeixisCandidates(sentence, reader.previous)),
    );
  }
  return findings;
}
