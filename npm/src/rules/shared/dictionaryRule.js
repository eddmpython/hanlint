// @ts-check
/** 사전 규칙의 공통 구현. cliche, translationese, redundantPair, japaneseLoan 이 사전 이름만 바꿔 쓴다. */
import { ERROR, SENTENCE, finding } from "../finding.js";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {string} dictionary
 * @param {string} ruleName
 * @param {string} [severity]
 * @returns {import("../finding.js").Finding[]}
 */
export function dictionaryFindings(doc, dictionary, ruleName, severity = ERROR) {
  const findings = [];
  for (const sentence of doc.sentences) {
    for (const match of sentence.matches) {
      if (match.dictionary !== dictionary) continue;
      const fix = match.fix !== null ? sentence.text.slice(0, match.start) + match.fix + sentence.text.slice(match.end) : null;
      findings.push(
        finding(ruleName, sentence.line, sentence.text, `\`${match.text}\` ${match.why} (${match.source})`, fix, severity, SENTENCE, sentence.index),
      );
    }
  }
  return findings;
}
