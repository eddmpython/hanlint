// @ts-check
/** Reader Contract 검사와 Patch 검증의 결정적 영수증. */

import { findingAsDict } from "../rules/finding.js";
import { compareText, surfaceViolationCount } from "./surface.js";

export const CHECK_MEANING = "violationCount는 선언한 보호 원자와 hanlint error의 수다. facts의 관계와 진실, 빠진 의미, 독자 효용과 자연스러움은 검증하지 않는다";
export const CHECK_MEANING_V2 = "violationCount는 선언한 보호 원자, 제목 구조와 hanlint error의 수다. facts의 관계와 진실, 빠진 의미, 독자 효용과 자연스러움은 검증하지 않는다";
export const PATCH_MEANING = "verified는 정확히 한 자리를 바꾸고 명시한 기존 위반을 줄이며 새 보호 원자 위반과 새 error를 만들지 않았다는 뜻뿐이다. 수정문의 의미와 진실, 자연스러움은 승인하지 않는다";
export const PATCH_MEANING_V2 = "verified는 정확히 한 자리를 바꾸고 명시한 기존 위반을 줄이며 새 보호 원자 위반, 새 제목 구조 위반과 새 error를 만들지 않았다는 뜻뿐이다. 수정문의 의미와 진실, 자연스러움은 승인하지 않는다";

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
  /** @param {string} contractSha256 @param {string} draftSha256 @param {import("./surface.js").SurfaceDiff} surface @param {import("../rules/finding.js").Finding[]} findings @param {number} [contractVersion] @param {import("./outline.js").OutlineDiff | null} [outline] @param {import("./outline.js").DocumentSummary | null} [document] */
  constructor(contractSha256, draftSha256, surface, findings, contractVersion = 1, outline = null, document = null) {
    this.contractSha256 = contractSha256;
    this.draftSha256 = draftSha256;
    this.surface = surface;
    this.findings = findings;
    this.contractVersion = contractVersion;
    this.outline = outline;
    this.document = document;
    if (![1, 2].includes(contractVersion)) {
      throw new Error(`check result contractVersion 은 1 또는 2다: ${contractVersion}`);
    }
    const hasStructure = outline !== null && document !== null;
    if (hasStructure !== (contractVersion === 2)) {
      throw new Error("version 2 check result만 outline과 document를 함께 가진다");
    }
  }

  get errorCount() {
    return this.findings.filter((finding) => finding.severity === "error").length;
  }

  get noticeCount() {
    return this.findings.length - this.errorCount;
  }

  get violationCount() {
    return surfaceViolationCount(this.surface) + (this.outline?.mismatches.length ?? 0) + this.errorCount;
  }

  asDict() {
    const result = {
      version: this.contractVersion,
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
      meaning: this.contractVersion === 1 ? CHECK_MEANING : CHECK_MEANING_V2,
    };
    if (this.contractVersion === 2) return { ...result, outline: this.outline, document: this.document };
    return result;
  }
}

export class PatchResult {
  /** @param {{contractSha256: string, sourceSha256: string, patchSha256: string, resultSha256: string | null, reason: string, matchCount: number, reasonBefore: number, reasonAfter: number | null, newContractIssues: [string, string][], newErrors: import("../rules/finding.js").Finding[], resultText: string | null, contractVersion: number}} values */
  constructor(values) {
    this.contractSha256 = values.contractSha256;
    this.sourceSha256 = values.sourceSha256;
    this.patchSha256 = values.patchSha256;
    this.resultSha256 = values.resultSha256;
    this.reason = values.reason;
    this.matchCount = values.matchCount;
    this.reasonBefore = values.reasonBefore;
    this.reasonAfter = values.reasonAfter;
    this.newContractIssues = values.newContractIssues;
    this.newErrors = values.newErrors;
    this.resultText = values.resultText;
    this.contractVersion = values.contractVersion;
    if (![1, 2].includes(values.contractVersion)) {
      throw new Error(`patch result contractVersion 은 1 또는 2다: ${values.contractVersion}`);
    }
  }

  get newSurfaceIssues() {
    return this.newContractIssues.filter(([kind]) => kind !== "outline");
  }

  get reasonReduced() {
    return this.reasonBefore > 0 && this.reasonAfter !== null && this.reasonAfter < this.reasonBefore;
  }

  get violationCount() {
    return Number(this.matchCount !== 1) + Number(!this.reasonReduced) + this.newContractIssues.length + this.newErrors.length;
  }

  get verified() {
    return this.violationCount === 0;
  }

  asDict() {
    const base = {
      version: this.contractVersion,
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
    };
    const issues = this.newContractIssues.map(([kind, value]) => ({ kind, value }));
    const tail = {
      newErrors: this.newErrors.map(findingAsDict),
      meaning: this.contractVersion === 1 ? PATCH_MEANING : PATCH_MEANING_V2,
    };
    if (this.contractVersion === 1) return { ...base, newSurfaceIssues: issues, ...tail };
    return { ...base, newContractIssues: issues, ...tail };
  }
}

/** 사람이 결론, 근거, 다음 행동 순서로 읽는 검사 영수증. @param {CheckResult} result */
export function renderCheck(result) {
  const lines = [result.violationCount === 0 ? "계약 위반 없음" : `계약 위반 ${result.violationCount}건`];
  const labels = [
    ["빠진 숫자", result.surface.missingNumbers],
    ["계약 밖 숫자", result.surface.unexpectedNumbers],
    ["빠진 URL", result.surface.missingUrls],
    ["계약 밖 URL", result.surface.unexpectedUrls],
    ["빠진 코드", result.surface.missingCode],
    ["계약 밖 코드", result.surface.unexpectedCode],
    ["빠진 링크 목적지", result.surface.missingLinks],
    ["계약 밖 링크 목적지", result.surface.unexpectedLinks],
  ];
  for (const [label, values] of labels) if (values.length) lines.push(`- ${label}: ${values.join(", ")}`);
  if (result.outline) {
    const state = result.outline.matches ? "일치" : `어긋남 ${result.outline.mismatches.length}곳`;
    lines.push(`- 구조: H${result.outline.level} ${result.outline.actual.length}개, ${state}`);
    for (const mismatch of result.outline.mismatches) {
      lines.push(`  ${mismatch.position}. 기대 \`${mismatch.expected ?? "없음"}\`, 실제 \`${mismatch.actual ?? "없음"}\``);
    }
  }
  if (result.document) {
    lines.push(`- 글: 문장 ${result.document.sentenceCount}, 문단 ${result.document.paragraphCount}, 절 ${result.document.sectionCount}`);
    result.document.sections.forEach((section, index) => {
      lines.push(`  ${index + 1}. ${section.heading} (${section.line}행, 문단 ${section.paragraphCount}, 코드 ${section.codeBlockCount})`);
    });
  }
  lines.push(`- lint: error ${result.errorCount}, notice ${result.noticeCount}`);
  if (result.errorCount) {
    lines.push(`  ${Object.entries(errorRules(result.findings)).map(([rule, count]) => `${rule} ${count}`).join(", ")}`);
  }
  if (result.violationCount) lines.push("\n다음: 계약과 글 가운데 틀린 쪽을 바로잡고 같은 check를 다시 실행한다");
  else if (result.noticeCount) lines.push("\n다음: notice를 읽고 고칠지 유지할지 판단한 뒤 사람과 LLM 평가로 넘어간다");
  else lines.push("\n다음: 세어서 잡히는 계약 위반이 없다. 사람과 LLM 평가로 넘어간다");
  lines.push("", result.contractVersion === 1 ? CHECK_MEANING : CHECK_MEANING_V2);
  return lines.join("\n");
}
