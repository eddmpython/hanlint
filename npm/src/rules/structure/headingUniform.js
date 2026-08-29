// @ts-check
import { DOCUMENT, finding } from "../finding.js";

export const name = "headingUniform";
export const mechanism = "repeat";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const headings = doc.headings.filter(([level]) => level === 2);
  // 버전이나 날짜처럼 숫자로 끝나는 제목은 어미가 아니라 판정에서 뺀다.
  const eligible = headings.filter(([, text]) => {
    if (!text.trim()) return false;
    const trimmed = text.trimEnd();
    const char = trimmed[trimmed.length - 1];
    return !(char >= "0" && char <= "9");
  });
  if (eligible.length < 3) return [];
  // 파이썬 Counter.most_common 은 같은 수면 먼저 들어온 것이 이긴다. 삽입 순서를 지킨다.
  /** @type {Map<string, number>} */
  const lastChars = new Map();
  for (const [, text] of eligible) {
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
  if (count / eligible.length >= config.headingUniformRatio) {
    return [
      finding(name, eligible[0][2], eligible.map(([, text]) => text).join(" / "), `H2 ${eligible.length}개 중 ${count}개가 \`${best}\` 로 끝난다. 목차가 한 어미로 끝나면 과정이 아니라 나열로 읽힌다. 형태를 섞는다`, null, "error", DOCUMENT, -1),
    ];
  }
  return [];
}
