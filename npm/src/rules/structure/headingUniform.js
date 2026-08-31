// @ts-check
import { DOCUMENT, finding } from "../finding.js";
import { shareOf } from "../shared/repeat.js";

export const name = "headingUniform";
export const mechanism = "repeat";

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const headings = doc.headings.filter(([level]) => level === 2);
  // 어미는 한글이다. 숫자, 부호, 라틴 문자로 끝나는 제목은 판정에서 뺀다. 파이썬과 같다.
  const eligible = headings.filter(([, text]) => {
    if (!text.trim()) return false;
    const trimmed = text.trimEnd();
    const char = trimmed[trimmed.length - 1];
    return char >= "가" && char <= "힣";
  });
  if (eligible.length < 3) return [];
  const [best, count, total] = shareOf(
    eligible.map(([, text]) => {
      const trimmed = text.trimEnd();
      return trimmed[trimmed.length - 1];
    }),
  );
  if (count / total >= config.headingUniformRatio) {
    return [
      finding(name, eligible[0][2], eligible.map(([, text]) => text).join(" / "), `H2 ${eligible.length}개 중 ${count}개가 \`${best}\` 로 끝난다. 목차가 한 어미로 끝나면 과정이 아니라 나열로 읽힌다. 그 문서의 관례라면 둔다`, null, "notice", DOCUMENT, -1),
    ];
  }
  return [];
}
