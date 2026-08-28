// @ts-check
/**
 * 사람이 읽는 지적 목록. `파일:줄` 로 시작해 편집기가 바로 연다. 파이썬 report/textReport.py 와 같은 글자다.
 * 끝에 본보기를 붙인다. 전과 후를 제 줄에 둔다. 왜 한 줄이 아닌지는 파이썬 report/textReport.py 가 소유한다.
 */
import { exemplarFor, shortened, twoLines } from "../data/exemplars.js";

/** 그 글에 나온 규칙의 본보기. 이름 순이고 규칙 하나에 세 줄이다. @param {import("../rules/finding.js").Finding[]} findings */
function exemplarLines(findings) {
  const lines = [];
  let cut = false;
  for (const name of [...new Set(findings.map((f) => f.rule))].sort()) {
    const exemplar = exemplarFor(name);
    if (!exemplar) continue;
    const [before, after] = twoLines(exemplar);
    cut = cut || shortened(exemplar);
    lines.push(`  [${name}]`, `    전  ${before}`, `    후  ${after}`);
  }
  if (!lines.length) return [];
  const head = "본보기 (고치기 전, 고친 뒤)";
  return [cut ? `${head}. 잘린 것은 hanlint explain <규칙>` : head, ...lines];
}

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
  lines.push(...exemplarLines(findings));
  return lines.join("\n").replace(/\n+$/, "");
}
