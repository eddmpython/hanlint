// @ts-check
/** 사전 규칙의 공통 구현. cliche, translationese, redundantPair, japaneseLoan 이 사전 이름만 바꿔 쓴다. */
import { fitJosa } from "../../analysis/josa.js";
import { ERROR, SENTENCE, finding } from "../finding.js";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {string} dictionary
 * @param {string} ruleName
 * @param {string} [severity]
 * @returns {import("../finding.js").Finding[]}
 */
/** 문장 시작부터 걸린 자리까지의 줄바꿈 수. 뜻은 파이썬 rules/shared/dictionaryRule.py 가 소유한다. @param {string} text */
function countNewlines(text) {
  let count = 0;
  for (const ch of text) if (ch === "\n") count += 1;
  return count;
}

export function dictionaryFindings(doc, dictionary, ruleName, severity = ERROR) {
  const findings = [];
  for (const sentence of doc.sentences) {
    for (const match of sentence.matches) {
      if (match.dictionary !== dictionary) continue;
      // 낱말만 갈아 끼우면 뒤에 붙은 조사가 틀어진다. `이슈로` 를 `쟁점로` 로 내밀던 자리다
      const tail = sentence.text.slice(match.end);
      const fix = match.fix !== null ? sentence.text.slice(0, match.start) + match.fix + fitJosa(match.fix, tail) : null;
      findings.push(
        finding(
          ruleName,
          sentence.line + countNewlines(sentence.text.slice(0, match.start)),
          sentence.text,
          `\`${match.text}\` ${match.why} (${match.source})`,
          fix,
          severity,
          SENTENCE,
          sentence.index,
          match.fix !== null ? match.text : null,
          match.fix,
        ),
      );
    }
  }
  return findings;
}
