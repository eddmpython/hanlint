// @ts-check
import { fitJosa } from "../../analysis/grammar/josa.js";
import { overlap } from "../../fingerprint/topics.js";
import { SENTENCE, finding } from "../finding.js";
import { danglingDeixisCandidates } from "../shared/candidates.js";
import { hasLocalAntecedent } from "../shared/localAntecedent.js";

export const name = "danglingDeixis";
export const mechanism = "reader";

const QUESTION = "의문";
const EXCLAIM = ["!", "！"];

/**
 * 앞 문장이 물음이나 감탄인가. 그러면 그 문장 자체가 지시어의 선행어다.
 * 뜻은 파이썬 rules/sentence/danglingDeixis.py 의 isPrompt 가 소유한다.
 * @param {{mood: string, text: string} | null} previous
 */
function isPrompt(previous) {
  if (!previous) return false;
  const text = previous.text.replace(/\s+$/u, "");
  return previous.mood === QUESTION || EXCLAIM.some((mark) => text.endsWith(mark));
}

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const sentence of doc.sentences) {
    if (!sentence.deixis.length) continue;
    if (hasLocalAntecedent(sentence)) continue;
    const reader = doc.reader.beforeSentence[sentence.index];
    if (overlap(reader.recent, sentence.topics) > 0) continue;
    if (isPrompt(reader.previous)) continue;
    findings.push(
      finding(name, sentence.line, sentence.text, `\`${sentence.deixis[0]}\` ${fitJosa(sentence.deixis[0], "이")} 가리킬 것이 앞 문장에 없다. 가리키는 파일, 값, 코드의 이름을 쓴다`, null, "error", SENTENCE, sentence.index, null, null, danglingDeixisCandidates(sentence, reader.previous)),
    );
  }
  return findings;
}
