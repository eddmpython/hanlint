// @ts-check
/**
 * 기계가 읽는 꼴. 평가 루프의 0층 입력이다. 파이썬 json.dumps(indent=2, ensure_ascii=False) 와 같은 글자다.
 * 지적마다 `exemplar` 를 붙인다. AI 는 규칙 이름과 이유만으로 고칠 때보다 본떠서 고칠 때 결과가 낫다.
 */
import { exemplarFor } from "../data/exemplars.js";
import { findingAsDict } from "../rules/finding.js";

/** @param {import("../rules/finding.js").Finding} finding */
function findingWithExemplar(finding) {
  const data = findingAsDict(finding);
  const exemplar = exemplarFor(finding.rule);
  if (exemplar) data.exemplar = { before: exemplar.before, after: exemplar.after, moved: exemplar.moved };
  return data;
}

/**
 * @param {Map<string, import("../rules/finding.js").Finding[]>} results
 * @param {string | null} [configLabel]
 */
export function renderJson(results, configLabel = null) {
  const files = [...results].map(([path, findings]) => ({ path, findings: findings.map(findingWithExemplar) }));
  /** @type {Record<string, unknown>} */
  const data = { version: 1 };
  if (configLabel !== null) data.config = configLabel;
  data.files = files;
  return JSON.stringify(data, null, 2);
}
