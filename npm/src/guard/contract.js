// @ts-check
/** Reader Contract 검사와 이유가 붙은 국소 Patch 검증. */
import { createHash } from "node:crypto";

import { Contract, Patch } from "../config/readerContract.js";
import { defaultConfig } from "../config/settings.js";
import { parseMarkdown } from "../document/parseMarkdown.js";
import { buildFingerprint } from "../fingerprint/build.js";
import { findingAsDict } from "../rules/finding.js";
import { runAll } from "../rules/registry.js";
import { compareText, factLines, surfaceDiff, surfaceViolationCount } from "./surface.js";

export const CHECK_MEANING = "violationCount는 선언한 보호 원자와 hanlint error의 수다. facts의 관계와 진실, 빠진 의미, 독자 효용과 자연스러움은 검증하지 않는다";
export const PATCH_MEANING = "verified는 정확히 한 자리를 바꾸고 명시한 기존 위반을 줄이며 새 보호 원자 위반과 새 error를 만들지 않았다는 뜻뿐이다. 수정문의 의미와 진실, 자연스러움은 승인하지 않는다";

/** @param {string} text */
function digest(text) {
  return createHash("sha256").update(text, "utf8").digest("hex");
}

/** @param {import("../rules/finding.js").Finding[]} findings */
function errorRules(findings) {
  /** @type {Record<string, number>} */
  const counted = {};
  for (const finding of findings) {
    if (finding.severity === "error") counted[finding.rule] = (counted[finding.rule] ?? 0) + 1;
  }
  return Object.fromEntries(Object.entries(counted).sort(([left], [right]) => compareText(left, right)));
}

export class CheckResult {
  /** @param {string} contractSha256 @param {string} draftSha256 @param {ReturnType<typeof surfaceDiff>} surface @param {import("../rules/finding.js").Finding[]} findings */
  constructor(contractSha256, draftSha256, surface, findings) {
    this.contractSha256 = contractSha256;
    this.draftSha256 = draftSha256;
    this.surface = surface;
    this.findings = findings;
  }

  get errorCount() {
    return this.findings.filter((finding) => finding.severity === "error").length;
  }

  get noticeCount() {
    return this.findings.length - this.errorCount;
  }

  get violationCount() {
    return surfaceViolationCount(this.surface) + this.errorCount;
  }

  asDict() {
    return {
      version: 1,
      kind: "hanlint.checkResult",
      violationCount: this.violationCount,
      contractSha256: this.contractSha256,
      draftSha256: this.draftSha256,
      surface: this.surface,
      lint: {
        errorCount: this.errorCount,
        noticeCount: this.noticeCount,
        errorRules: errorRules(this.findings),
        items: this.findings.map(findingAsDict),
      },
      meaning: CHECK_MEANING,
    };
  }
}

export class PatchResult {
  /** @param {{contractSha256: string, sourceSha256: string, patchSha256: string, resultSha256: string | null, reason: string, matchCount: number, reasonBefore: number, reasonAfter: number | null, newSurfaceIssues: [string, string][], newErrors: import("../rules/finding.js").Finding[], resultText: string | null}} values */
  constructor(values) {
    this.contractSha256 = values.contractSha256;
    this.sourceSha256 = values.sourceSha256;
    this.patchSha256 = values.patchSha256;
    this.resultSha256 = values.resultSha256;
    this.reason = values.reason;
    this.matchCount = values.matchCount;
    this.reasonBefore = values.reasonBefore;
    this.reasonAfter = values.reasonAfter;
    this.newSurfaceIssues = values.newSurfaceIssues;
    this.newErrors = values.newErrors;
    this.resultText = values.resultText;
  }

  get reasonReduced() {
    return this.reasonBefore > 0 && this.reasonAfter !== null && this.reasonAfter < this.reasonBefore;
  }

  get violationCount() {
    return Number(this.matchCount !== 1) + Number(!this.reasonReduced) + this.newSurfaceIssues.length + this.newErrors.length;
  }

  get verified() {
    return this.violationCount === 0;
  }

  asDict() {
    return {
      version: 1,
      kind: "hanlint.patchResult",
      verified: this.verified,
      violationCount: this.violationCount,
      contractSha256: this.contractSha256,
      sourceSha256: this.sourceSha256,
      patchSha256: this.patchSha256,
      resultSha256: this.resultSha256,
      matchCount: this.matchCount,
      reason: {
        name: this.reason,
        before: this.reasonBefore,
        after: this.reasonAfter,
        reduced: this.reasonReduced,
      },
      newSurfaceIssues: this.newSurfaceIssues.map(([kind, value]) => ({ kind, value })),
      newErrors: this.newErrors.map(findingAsDict),
      meaning: PATCH_MEANING,
    };
  }
}

/** 원문의 보호 표면을 모두 덮는 version 1 Contract 초안을 만든다. @param {string} text @param {string} reader @param {string} goal */
export function contractFromText(text, reader, goal) {
  const contract = new Contract(reader, goal, factLines(text));
  const result = surfaceDiff(contract.text, text);
  const missing = [];
  for (const kind of ["missingNumbers", "missingUrls", "missingCode", "missingLinks"]) {
    for (const value of result[/** @type {keyof typeof result} */ (kind)]) missing.push(`${kind}=${value}`);
  }
  if (missing.length) throw new Error(`reader 또는 goal이 원문에 없는 보호 원자를 넣었다: ${missing.join(", ")}`);
  if (surfaceViolationCount(result)) {
    const issues = Object.entries(result).flatMap(([kind, values]) => values.map((value) => `${kind}=${value}`));
    throw new Error(`계약 초안이 원문의 보호 표면을 모두 담지 못했다: ${issues.join(", ")}`);
  }
  return contract;
}

/** @param {string} text @param {Contract | Record<string, unknown>} rawContract @param {import("../config/settings.js").Config} [config] @param {string | null} [path] */
export function check(text, rawContract, config = defaultConfig(), path = null) {
  const contract = rawContract instanceof Contract ? rawContract : Contract.fromMapping(rawContract);
  const findings = runAll(buildFingerprint(parseMarkdown(text, path), config), config);
  return new CheckResult(contract.digest, digest(text), surfaceDiff(contract.text, text), findings);
}

/** @param {CheckResult} result */
function surfaceIssues(result) {
  const found = new Set();
  for (const [kind, values] of Object.entries(result.surface)) {
    for (const value of values) found.add(`${kind}\u0000${value}`);
  }
  return found;
}

/** @param {CheckResult} result @param {string} reason */
function reasonCount(result, reason) {
  if (reason in result.surface) return result.surface[/** @type {keyof typeof result.surface} */ (reason)].length;
  return result.findings.filter((finding) => finding.rule === reason).length;
}

/** @param {import("../rules/finding.js").Finding} finding */
function errorSignature(finding) {
  return `${finding.rule}\u0000${finding.quote}`;
}

/** @param {CheckResult} before @param {CheckResult} after */
function addedErrors(before, after) {
  const remaining = new Map();
  for (const finding of before.findings) {
    if (finding.severity !== "error") continue;
    const signature = errorSignature(finding);
    remaining.set(signature, (remaining.get(signature) ?? 0) + 1);
  }
  return after.findings.filter((finding) => {
    if (finding.severity !== "error") return false;
    const signature = errorSignature(finding);
    const count = remaining.get(signature) ?? 0;
    if (!count) return true;
    remaining.set(signature, count - 1);
    return false;
  });
}

/** 파이썬 str.count와 같은 겹치지 않는 정확 출현 수. @param {string} text @param {string} fragment */
function exactCount(text, fragment) {
  let count = 0;
  let cursor = 0;
  while (true) {
    const at = text.indexOf(fragment, cursor);
    if (at < 0) return count;
    count += 1;
    cursor = at + fragment.length;
  }
}

/** @param {string} text @param {Patch | Record<string, unknown>} rawPatch @param {Contract | Record<string, unknown>} rawContract @param {import("../config/settings.js").Config} [config] @param {string | null} [path] */
export function verifyPatch(text, rawPatch, rawContract, config = defaultConfig(), path = null) {
  const patch = rawPatch instanceof Patch ? rawPatch : Patch.fromMapping(rawPatch);
  const contract = rawContract instanceof Contract ? rawContract : Contract.fromMapping(rawContract);
  const beforeResult = check(text, contract, config, path);
  const matchCount = exactCount(text, patch.before);
  const reasonBefore = reasonCount(beforeResult, patch.reason);
  if (matchCount !== 1) {
    return new PatchResult({
      contractSha256: contract.digest,
      sourceSha256: beforeResult.draftSha256,
      patchSha256: patch.digest,
      resultSha256: null,
      reason: patch.reason,
      matchCount,
      reasonBefore,
      reasonAfter: null,
      newSurfaceIssues: [],
      newErrors: [],
      resultText: null,
    });
  }
  const resultText = text.replace(patch.before, patch.after);
  const afterResult = check(resultText, contract, config, path);
  const beforeSurface = surfaceIssues(beforeResult);
  const newSurfaceIssues = [...surfaceIssues(afterResult)]
    .filter((issue) => !beforeSurface.has(issue))
    .map((issue) => /** @type {[string, string]} */ (issue.split("\u0000", 2)))
    .sort((left, right) => compareText(left[0], right[0]) || compareText(left[1], right[1]));
  return new PatchResult({
    contractSha256: contract.digest,
    sourceSha256: beforeResult.draftSha256,
    patchSha256: patch.digest,
    resultSha256: afterResult.draftSha256,
    reason: patch.reason,
    matchCount,
    reasonBefore,
    reasonAfter: reasonCount(afterResult, patch.reason),
    newSurfaceIssues,
    newErrors: addedErrors(beforeResult, afterResult),
    resultText,
  });
}
