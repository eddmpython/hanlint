// @ts-check
/** 기계가 읽는 꼴. 평가 루프의 0층 입력이다. 파이썬 json.dumps(indent=2, ensure_ascii=False) 와 같은 글자다. */
import { findingAsDict } from "../rules/finding.js";

/**
 * @param {Map<string, import("../rules/finding.js").Finding[]>} results
 * @param {string | null} [configLabel]
 */
export function renderJson(results, configLabel = null) {
  const files = [...results].map(([path, findings]) => ({ path, findings: findings.map(findingAsDict) }));
  /** @type {Record<string, unknown>} */
  const data = { version: 1 };
  if (configLabel !== null) data.config = configLabel;
  data.files = files;
  return JSON.stringify(data, null, 2);
}
