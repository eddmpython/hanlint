// @ts-check
import { DOCUMENT, finding } from "../finding.js";

export const name = "headingUniform";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const headings = doc.headings.filter(([level]) => level === 2);
  if (headings.length < 3) return [];
  // 파이썬 Counter.most_common 은 같은 수면 먼저 들어온 것이 이긴다. 삽입 순서를 지킨다.
  /** @type {Map<string, number>} */
  const lastChars = new Map();
  for (const [, text] of headings) {
    if (!text.trim()) continue;
    const trimmed = text.trimEnd();
    const char = trimmed[trimmed.length - 1];
    lastChars.set(char, (lastChars.get(char) ?? 0) + 1);
  }
  let best = "";
  let count = -1;
  for (const [char, n] of lastChars) {
    if (n > count) {
      best = char;
      count = n;
    }
  }
  if (count / headings.length >= config.headingUniformRatio) {
    return [
      finding(name, headings[0][2], headings.map(([, text]) => text).join(" / "), `H2 ${headings.length}개 중 ${count}개가 \`${best}\` 로 끝난다. 목차가 한 어미로 끝나면 과정이 아니라 나열로 읽힌다. 형태를 섞는다`, null, "error", DOCUMENT, -1),
    ];
  }
  return [];
}
