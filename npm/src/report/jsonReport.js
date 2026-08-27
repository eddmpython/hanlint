// @ts-check
/** 기계가 읽는 꼴. 평가 루프의 0층 입력이다. 파이썬 json.dumps(indent=2, ensure_ascii=False) 와 같은 글자다. */
import { findingAsDict } from "../rules/finding.js";

/** @param {Map<string, import("../rules/finding.js").Finding[]>} results */
export function renderJson(results) {
  const files = [...results].map(([path, findings]) => ({ path, findings: findings.map(findingAsDict) }));
  return JSON.stringify({ version: 1, files }, null, 2);
}
