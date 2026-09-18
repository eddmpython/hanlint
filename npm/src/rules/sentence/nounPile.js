// @ts-check
import { nounRuns } from "../../analysis/index.js";
import { attested, usageKindOf } from "../../usage/counts.js";
import { SENTENCE, finding } from "../finding.js";

export const name = "nounPile";
export const mechanism = "threshold";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const findings = [];
  const kind = usageKindOf(config);
  for (const sentence of doc.sentences) {
    if (sentence.nounRun < config.nounPileMin) continue;
    if (kind) {
      const piles = nounRuns(sentence.text).filter(([, length]) => length >= config.nounPileMin).map(([chain]) => chain);
      if (piles.length && piles.every((chain) => attested(chain, kind, config.usageMin))) continue;
    }
    findings.push(
      finding(name, sentence.line, sentence.text, `명사 ${sentence.nounRun}개가 조사 없이 이어진다. 관계가 표시되지 않아 독자가 조사를 끼워 넣는다. 동사로 되돌린다`, null, config.enforceStyle.includes(name) ? "error" : "notice", SENTENCE, sentence.index),
    );
  }
  return findings;
}
