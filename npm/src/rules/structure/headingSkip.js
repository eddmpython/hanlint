// @ts-check
import { DOCUMENT, finding } from "../finding.js";

export const name = "headingSkip";
export const mechanism = "threshold";

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  /** @type {number | null} */
  let previous = doc.frontmatter.title ? 1 : null;
  for (const [level, text, line] of doc.headings) {
    if (previous !== null && level > previous + 1) {
      findings.push(finding(name, line, text, `H${previous} 다음에 H${level} 이 온다. 한 수준씩 내려간다`, null, "error", DOCUMENT, -1));
    }
    previous = level;
  }
  return findings;
}
