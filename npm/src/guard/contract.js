// @ts-check
/** Reader Contract 검사와 이유가 붙은 국소 Patch 검증. */
import { createHash } from "node:crypto";

import { Patch } from "../config/patch.js";
import { Contract, ContractV2, Outline, ProtectedSurface, parseContract } from "../config/readerContract.js";
import { defaultConfig } from "../config/settings.js";
import { headingsOf } from "../document/model.js";
import { parseMarkdown } from "../document/parseMarkdown.js";
import { buildFingerprint } from "../fingerprint/build.js";
import { runAll } from "../rules/registry.js";
import { compareOutline, summarizeDocument } from "./outline.js";
import { CheckResult, PatchResult } from "./receipt.js";
import { compareText, factLines, protectedSurface, surfaceDiff, surfaceViolationCount } from "./surface.js";

/** @param {string} text */
function digest(text) {
  return createHash("sha256").update(text, "utf8").digest("hex");
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

/** 원문의 자동 표면과 한 수준의 제목을 분리한 version 2 Contract 초안을 만든다. @param {string} text @param {string} reader @param {string} goal @param {number} [outlineLevel] @param {string[]} [facts] */
export function contractFromTextV2(text, reader, goal, outlineLevel = 2, facts = []) {
  const doc = parseMarkdown(text);
  const headings = headingsOf(doc, outlineLevel).map((heading) => heading.text);
  const surface = protectedSurface(text);
  const contract = new ContractV2(
    reader,
    goal,
    facts,
    new ProtectedSurface(surface.numbers, surface.urls, surface.code, surface.links),
    new Outline(outlineLevel, headings),
  );
  const result = surfaceDiff(contract.text, text);
  if (surfaceViolationCount(result)) {
    const issues = Object.entries(result).flatMap(([kind, values]) => values.map((value) => `${kind}=${value}`));
    throw new Error(`reader, goal 또는 facts가 원문에 없는 보호 원자를 넣었다: ${issues.join(", ")}`);
  }
  return contract;
}

/** @param {string} text @param {Contract | ContractV2 | Record<string, unknown>} rawContract @param {import("../config/settings.js").Config} [config] @param {string | null} [path] */
export function check(text, rawContract, config = defaultConfig(), path = null) {
  const contract = rawContract instanceof Contract || rawContract instanceof ContractV2 ? rawContract : parseContract(rawContract);
  const doc = buildFingerprint(parseMarkdown(text, path), config);
  const findings = runAll(doc, config);
  const outline = contract instanceof ContractV2 ? compareOutline(contract.outline, doc) : null;
  const document = contract instanceof ContractV2 ? summarizeDocument(doc) : null;
  return new CheckResult(contract.digest, digest(text), surfaceDiff(contract.text, text), findings, contract.version, outline, document);
}

/** @param {CheckResult} result */
function contractIssues(result) {
  const found = new Set();
  for (const [kind, values] of Object.entries(result.surface)) {
    for (const value of values) found.add(`${kind}\u0000${value}`);
  }
  if (result.outline) {
    for (const mismatch of result.outline.mismatches) {
      found.add(`outline\u0000${mismatch.position}:${mismatch.expected ?? ""}:${mismatch.actual ?? ""}`);
    }
  }
  return found;
}

/** @param {CheckResult} result @param {string} reason */
function reasonCount(result, reason) {
  if (reason in result.surface) return result.surface[/** @type {keyof typeof result.surface} */ (reason)].length;
  if (reason === "outline" && result.outline) return result.outline.mismatches.length;
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

/** @param {string} text @param {Patch | Record<string, unknown>} rawPatch @param {Contract | ContractV2 | Record<string, unknown>} rawContract @param {import("../config/settings.js").Config} [config] @param {string | null} [path] */
export function verifyPatch(text, rawPatch, rawContract, config = defaultConfig(), path = null) {
  const patch = rawPatch instanceof Patch ? rawPatch : Patch.fromMapping(rawPatch);
  const contract = rawContract instanceof Contract || rawContract instanceof ContractV2 ? rawContract : parseContract(rawContract);
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
      newContractIssues: [],
      newErrors: [],
      resultText: null,
      contractVersion: contract.version,
    });
  }
  const resultText = text.replace(patch.before, patch.after);
  const afterResult = check(resultText, contract, config, path);
  const beforeIssues = contractIssues(beforeResult);
  const newContractIssues = [...contractIssues(afterResult)]
    .filter((issue) => !beforeIssues.has(issue))
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
    newContractIssues,
    newErrors: addedErrors(beforeResult, afterResult),
    resultText,
    contractVersion: contract.version,
  });
}
