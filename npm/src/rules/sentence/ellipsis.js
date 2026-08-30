// @ts-check
import { insideAny } from "../../fingerprint/markers.js";
import { SENTENCE, finding } from "../finding.js";

export const name = "ellipsis";
export const mechanism = "dictionary";
// 영숫자에 붙은 점 셋 (`v0.0.1...HEAD`, compare URL) 은 범위 표기라 말줄임표가 아니다.
// 인라인 코드와 따옴표 안은 지문이 인용 구간으로 이미 표시해 두었으므로 여기서 다시 재지 않는다.
const ELLIPSIS = /(?<![A-Za-z0-9])(…|\.{3,})(?![A-Za-z0-9])/g;
const CLI_OPTION = /(?:^|\s)--?[A-Za-z0-9]/;

/** 괄호 안 명령 예시의 생략 인자. 예: (kubectl get -o yaml …). @param {string} text @param {number} start @param {number} end */
function insideCommandExample(text, start, end) {
  const opened = text.lastIndexOf("(", start);
  const closed = text.indexOf(")", end);
  return opened >= 0 && closed >= 0 && !text.slice(opened, start).includes(")") && !text.slice(end, closed).includes("(") && CLI_OPTION.test(text.slice(opened + 1, closed));
}

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  for (const sentence of doc.sentences) {
    const found = [...sentence.text.matchAll(ELLIPSIS)].filter((m) => {
      const start = /** @type {number} */ (m.index);
      return !insideAny(start, start + m[0].length, sentence.quoted) && !insideCommandExample(sentence.text, start, start + m[0].length);
    });
    if (found.length) {
      findings.push(finding(name, sentence.line, sentence.text, "말줄임표로 말끝을 흐리면 독자가 결론을 받아 가지 못한다. 문장을 끝까지 쓴다", null, "error", SENTENCE, sentence.index));
    }
  }
  return findings;
}
