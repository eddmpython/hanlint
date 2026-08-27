// @ts-check
import { SENTENCE, finding } from "../finding.js";

export const name = "doubleNegative";
const DOUBLE_NEGATIVE = /(하지 않으면 안 (?:된다|됩니다)|하지 않을 수 없(?:다|습니다)|지 않으면 안 (?:된다|됩니다)|지 않을 수 없(?:다|습니다))/;
/** @type {Record<string, string>} */
const FIXES = {
  "하지 않으면 안 된다": "해야 한다",
  "하지 않으면 안 됩니다": "해야 합니다",
  "하지 않을 수 없다": "한다",
  "하지 않을 수 없습니다": "합니다",
};

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const sentence of doc.sentences) {
    const match = DOUBLE_NEGATIVE.exec(sentence.text);
    if (!match) continue;
    const replacement = FIXES[match[1]];
    const start = /** @type {number} */ (match.index);
    const fix = replacement ? sentence.text.slice(0, start) + replacement + sentence.text.slice(start + match[0].length) : null;
    findings.push(
      finding(name, sentence.line, sentence.text, `\`${match[1]}\` 는 이중 부정이다. 긍정으로 쓴다`, fix, "error", SENTENCE, sentence.index, replacement ? match[1] : null, replacement ?? null),
    );
  }
  return findings;
}
