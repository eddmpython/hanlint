// @ts-check
/** 한 줄에 지적 하나. AI 와 스크립트가 읽는 형식이다. 파이썬 report/compactReport.py 와 같은 글자다. */

/** 줄바꿈과 이어진 공백을 하나로 눕힌다. 한 줄은 이 형식의 계약이다. @param {string} text */
function flat(text) {
  return text.split(/\s+/).filter(Boolean).join(" ");
}

/** @param {string} path @param {import("../rules/finding.js").Finding[]} findings */
export function renderCompact(path, findings) {
  return findings
    .map((f) => {
      const label = f.severity === "notice" ? "notice: " : "";
      const fixLabel = f.severity === "notice" ? "검토할 대안" : "고친 뒤";
      return `${path}:${f.line} [${f.rule}] ${label}${flat(f.why)}` + (f.fix ? `  ${fixLabel}: ${flat(f.fix)}` : "");
    })
    .join("\n");
}
