// @ts-check
/** 선택한 규칙의 Finding 줄과 원문 변경 창을 대조한다. */
export function editIssues(text, patch, findings, policy) {
  if (!Object.keys(policy).length) return [];
  const limits = policy[patch.reason];
  if (!limits) return [["editPolicy", "reason has no edit budget"]];
  const before = [...patch.before], after = [...patch.after];
  let prefix = 0, suffix = 0;
  while (prefix < Math.min(before.length, after.length) && before[prefix] === after[prefix]) prefix++;
  while (suffix < Math.min(before.length, after.length) - prefix && before.at(-1 - suffix) === after.at(-1 - suffix)) suffix++;
  const changedBefore = before.slice(prefix, before.length - suffix).join("");
  const changedAfter = after.slice(prefix, after.length - suffix).join("");
  const start = text.indexOf(patch.before) + before.slice(0, prefix).join("").length;
  const firstLine = text.slice(0, start).split("\n").length;
  const lastLine = firstLine + changedBefore.split("\n").length - 1;
  const issues = [];
  if (!findings.some((f) => f.rule === patch.reason && firstLine <= f.line && f.line <= lastLine)) {
    issues.push(["editPolicy", "changed range does not contain the Finding line"]);
  }
  if (Math.max([...changedBefore].length, [...changedAfter].length) > limits.maxChars) {
    issues.push(["editPolicy", "changed range exceeds maxChars"]);
  }
  if (Math.max(changedBefore.split("\n").length, changedAfter.split("\n").length) > limits.maxLines) {
    issues.push(["editPolicy", "changed range exceeds maxLines"]);
  }
  return issues;
}
