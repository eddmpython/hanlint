// @ts-check
/** GitHub Actions 의 워크플로 명령 꼴. PR 에 줄 단위 주석이 붙는다. */

/** @param {string} path @param {import("../rules/finding.js").Finding[]} findings */
export function renderGithub(path, findings) {
  return findings
    .map((f) => {
      const level = f.severity === "error" ? "error" : "notice";
      const message = `[${f.rule}] ${f.why}`.replace(/\n/g, " ");
      return `::${level} file=${path},line=${f.line}::${message}`;
    })
    .join("\n");
}
