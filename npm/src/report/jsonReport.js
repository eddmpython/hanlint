// @ts-check
/**
 * 기계가 읽는 꼴. 평가 루프의 0층 입력이다. 파이썬 json.dumps(indent=2, ensure_ascii=False) 와 같은 글자다.
 * 지적마다 `exemplar` 를 붙인다. 승인 원문 완전 일치 `patch`는 맞는 지적에만 별도로 붙인다.
 * 실제 수정 차이는 파이썬의 exemplarLift와 patchMemory 탐침에서 따로 잰다.
 */
import { exemplarFor } from "../data/exemplars.js";
import { findingAsDict } from "../rules/finding.js";
import { exemplarInRegister } from "./registerMatch.js";
import { operationGuidance } from "./operationMatch.js";
import { patchData } from "./patchMatch.js";

/** @param {import("../rules/finding.js").Finding} finding @param {string | null | undefined} register @param {string | null | undefined} preset @param {import("../data/exemplars.js").Exemplar[]} customExemplars */
function findingWithExemplar(finding, document, register, preset, customExemplars, patches) {
  const data = findingAsDict(finding);
  const exemplar = exemplarFor(finding.rule, preset, customExemplars);
  if (exemplar) {
    const adapted = exemplarInRegister(exemplar, register);
    data.exemplar = { before: adapted.before, after: adapted.after, moved: adapted.moved };
  }
  const selected = patchData(document, finding, preset, patches);
  if (selected) data.patch = selected;
  return data;
}

/**
 * @param {Map<string, import("../rules/finding.js").Finding[]>} results
 * @param {string | null} [configLabel]
 * @param {Map<string, string> | null} [registers]
 * @param {string | null} [preset]
 * @param {import("../data/exemplars.js").Exemplar[]} [customExemplars]
 * @param {Map<string, import("../fingerprint/build.js").DocumentPrint> | null} [documents]
 * @param {import("../data/patches.js").Patch[]} [patches]
 * @param {import("../data/operations.js").SurfaceOperation[]} [operations]
 * @param {string[]} [protectedTerms]
 */
export function renderJson(
  results,
  configLabel = null,
  registers = null,
  preset = null,
  customExemplars = [],
  documents = null,
  patches = [],
  operations = [],
  protectedTerms = [],
) {
  const files = [...results].map(([path, findings]) => {
    const document = documents?.get(path);
    const entry = {
      path,
      findings: findings.map((finding) => findingWithExemplar(finding, document, registers?.get(path), preset, customExemplars, patches)),
    };
    const selectedOperations = operationGuidance(document, findings, preset, operations, patches, protectedTerms);
    if (selectedOperations.length) entry.operations = selectedOperations;
    return entry;
  });
  /** @type {Record<string, unknown>} */
  const data = { version: 1 };
  if (configLabel !== null) data.config = configLabel;
  data.files = files;
  return JSON.stringify(data, null, 2);
}
