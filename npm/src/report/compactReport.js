// @ts-check
/** 한 줄에 지적 하나. AI 와 스크립트가 읽는 꼴이다. 파이썬 report/compactReport.py 와 같은 글자다. */

/** 줄바꿈과 이어진 공백을 하나로 눕힌다. 한 줄은 이 꼴의 계약이다. @param {string} text */
function flat(text) {
  return text.split(/\s+/).filter(Boolean).join(" ");
}

/** @param {string} path @param {import("../rules/finding.js").Finding[]} findings */
export function renderCompact(path, findings) {
  return findings
    .map((f) => `${path}:${f.line} [${f.rule}] ${flat(f.why)}` + (f.fix ? `  고친 뒤: ${flat(f.fix)}` : ""))
    .join("\n");
}
