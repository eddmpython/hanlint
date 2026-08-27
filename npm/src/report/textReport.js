// @ts-check
/** 사람이 읽는 지적 목록. `파일:줄` 로 시작해 편집기가 바로 연다. 파이썬 report/textReport.py 와 같은 글자다. */

/** @param {string} path @param {import("../rules/finding.js").Finding[]} findings */
export function renderText(path, findings) {
  if (!findings.length) return `${path}  집은 자리 없음`;
  const errors = findings.filter((f) => f.severity === "error").length;
  const notices = findings.length - errors;
  const summary = `${path}  집은 자리 ${errors}` + (notices ? `, 확인할 자리 ${notices}` : "");
  const lines = [summary, ""];
  for (const f of findings) {
    const tag = `[${f.rule}]` + (f.severity === "notice" ? " 확인" : "");
    lines.push(`${path}:${f.line}  ${tag}`, `  ${f.quote}`, `  ${f.why}`);
    if (f.fix) lines.push(`  고친 뒤: ${f.fix}`);
    lines.push("");
  }
  return lines.join("\n").replace(/\n+$/, "");
}
