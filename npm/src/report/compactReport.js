// @ts-check
/** 한 줄에 지적 하나. AI 와 스크립트가 읽는 꼴이다. 파이썬 report/compactReport.py 와 같은 글자다. */

/** @param {string} path @param {import("../rules/finding.js").Finding[]} findings */
export function renderCompact(path, findings) {
  return findings
    .map((f) => `${path}:${f.line} [${f.rule}] ${f.why}` + (f.fix ? `  고친 뒤: ${f.fix}` : ""))
    .join("\n");
}
