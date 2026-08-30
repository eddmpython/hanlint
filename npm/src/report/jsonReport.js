// @ts-check
/**
 * 기계가 읽는 꼴. 평가 루프의 0층 입력이다. 파이썬 json.dumps(indent=2, ensure_ascii=False) 와 같은 글자다.
 * 지적마다 `exemplar` 를 붙인다. 실제 수정 차이는 파이썬의 exemplarLift 탐침에서 따로 잰다.
 */
import { exemplarFor } from "../data/exemplars.js";
import { findingAsDict } from "../rules/finding.js";
import { exemplarInRegister } from "./registerMatch.js";

/** @param {import("../rules/finding.js").Finding} finding @param {string | null | undefined} register @param {string | null | undefined} preset @param {import("../data/exemplars.js").Exemplar[]} customExemplars */
function findingWithExemplar(finding, register, preset, customExemplars) {
  const data = findingAsDict(finding);
  const exemplar = exemplarFor(finding.rule, preset, customExemplars);
  if (exemplar) {
    const adapted = exemplarInRegister(exemplar, register);
    data.exemplar = { before: adapted.before, after: adapted.after, moved: adapted.moved };
  }
  return data;
}

/**
 * @param {Map<string, import("../rules/finding.js").Finding[]>} results
 * @param {string | null} [configLabel]
 * @param {Map<string, string> | null} [registers]
 * @param {string | null} [preset]
 * @param {import("../data/exemplars.js").Exemplar[]} [customExemplars]
 */
export function renderJson(results, configLabel = null, registers = null, preset = null, customExemplars = []) {
  const files = [...results].map(([path, findings]) => ({
    path,
    findings: findings.map((finding) => findingWithExemplar(finding, registers?.get(path), preset, customExemplars)),
  }));
  /** @type {Record<string, unknown>} */
  const data = { version: 1 };
  if (configLabel !== null) data.config = configLabel;
  data.files = files;
  return JSON.stringify(data, null, 2);
}
