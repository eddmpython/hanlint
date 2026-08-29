// @ts-check
import { SENTENCE, finding } from "../finding.js";
import { COPULA as COPULA_KIND, lastWord, parsePredicate } from "../../analysis/grammar/index.js";

export const name = "negationRedefine";
export const mechanism = "repeat";
const NEGATION = /단순(?:한|히)\s?.{0,15}?(?:이|가)\s?아(?:닙니다|니다|니에요|니죠|닌)/;
const COPULA = /(입니다|이다|이에요|예요)[.!]?$/;

/** @param {string} text */
function isDefinition(text) {
  if (COPULA.test(text.trim())) return true;
  const predicate = parsePredicate(lastWord(text));
  return predicate !== null && predicate.kind === COPULA_KIND;
}

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const paragraph of doc.paragraphs) {
    const sentences = paragraph.sentences;
    for (let i = 0; i + 1 < sentences.length; i++) {
      const current = sentences[i];
      const following = sentences[i + 1];
      if (NEGATION.test(current.text) && isDefinition(following.text)) {
        findings.push(finding(name, current.line, current.text, "단순한 X 가 아닙니다 뒤에 Y 입니다 로 재정의하는 공식이다. 앞 문장을 지우고 Y 를 바로 쓴다", null, "error", SENTENCE, current.index));
      }
    }
  }
  return findings;
}
