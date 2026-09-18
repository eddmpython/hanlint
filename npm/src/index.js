// @ts-check
/**
 * hanlint: 한국어 글에서 AI 와 사람이 반복해서 어기는 결함을 결정적으로 잡는 린터. 공개 표면은 이 파일 한 곳이다.
 *
 * ```js
 * import { lintText, lintFile } from "hanlint";
 * for (const f of lintFile("글.md")) console.log(f.line, f.rule, f.why);
 * ```
 *
 * 합격과 불합격을 판정하지 않는다. 지적 목록이 비어 있다는 것은 세어서 잡히는 결함이 없다는 뜻이다.
 * 같은 공개 API를 Node와 브라우저가 공유한다. 파일 경로를 읽는 API만 Node 전용이다.
 */
import { readExternal } from "./data/read.js";
import { Patch } from "./config/patch.js";
import {
  CONTRACT_VERSION,
  CONTRACT_VERSIONS,
  LATEST_CONTRACT_VERSION,
  Contract,
  ContractV2,
  Outline,
  ProtectedSurface,
  parseContract,
} from "./config/readerContract.js";
import { configFromMapping, defaultConfig } from "./config/settings.js";
import { loadVersion } from "./data/load.js";
import { parseMarkdown } from "./document/parseMarkdown.js";
import { SOURCE_SUFFIXES, replaceLiteral, sourceLiterals } from "./document/sourceText.js";
import { applyRows, parseSheet, renderSheet, renderSheetJson, sheetRows } from "./report/sheet.js";
import { headingsOf } from "./document/model.js";
import { applyFixes } from "./edit/applyFixes.js";
import { buildFingerprint } from "./fingerprint/build.js";
import { fingerprintDict } from "./report/fingerprintJson.js";
import { check, contractFromText, contractFromTextV2, verifyPatch } from "./guard/contract.js";
import { CheckResult, PatchResult, renderCheck } from "./guard/receipt.js";
import { compareOutline } from "./guard/outline.js";
import { protectedSurface, surfaceDiff } from "./guard/surface.js";
import { ruleDoc, ruleNames, ruleSummary, runAll } from "./rules/registry.js";
import { renderJson } from "./report/jsonReport.js";
import { learnExemplars } from "./learn/edits.js";
import { learnOperations } from "./learn/operations.js";

const nodeConfig = typeof process === "object" && process.versions?.node ? await import("./config/loadConfig.js") : null;

/** Node 파일 설정. 브라우저에서는 configFromMapping에 설정 객체를 전달한다. @param {string | null} path @param {string | null} start */
export function loadConfig(path = null, start = null) {
  if (!nodeConfig) throw new Error("브라우저에서는 configFromMapping으로 설정 객체를 전달해 주세요.");
  return nodeConfig.loadConfig(path, start);
}

export {
  CheckResult,
  SOURCE_SUFFIXES,
  parseSheet,
  renderSheet,
  renderSheetJson,
  sheetRows,
  applyRows,
  replaceLiteral,
  sourceLiterals,
  CONTRACT_VERSION,
  CONTRACT_VERSIONS,
  Contract,
  ContractV2,
  LATEST_CONTRACT_VERSION,
  Outline,
  Patch,
  PatchResult,
  ProtectedSurface,
  applyFixes,
  check,
  contractFromText,
  contractFromTextV2,
  configFromMapping,
  defaultConfig,
  fingerprintDict,
  parseContract,
  renderCheck,
  ruleDoc,
  ruleNames,
  ruleSummary,
  verifyPatch,
};
export const version = loadVersion();

/**
 * 글을 한 번 읽어 지문을 만든다.
 * @param {string} text
 * @param {import("./config/settings.js").Config} [config]
 * @param {string | null} [path]
 */
export function fingerprint(text, config = defaultConfig(), path = null) {
  return buildFingerprint(parseMarkdown(text, path), config);
}

/**
 * 문자열을 검사해 줄 번호 순의 지적 목록을 준다.
 * @param {string} text
 * @param {import("./config/settings.js").Config} [config]
 * @param {string | null} [path]
 */
export function lintText(text, config = defaultConfig(), path = null) {
  return runAll(fingerprint(text, config, path), config);
}

/**
 * 파일을 UTF-8 로 읽어 검사한다.
 * @param {string} path
 * @param {import("./config/settings.js").Config} [config]
 */
export function lintFile(path, config = defaultConfig()) {
  return lintText(readExternal(path), config, path);
}

/** 지적, 문체 본보기, 승인 고침과 지문을 같은 분석에서 제공한다. @param {string} text @param {import("./config/settings.js").Config} config */
export function inspectText(text, config = defaultConfig()) {
  const document = fingerprint(text, config);
  const findings = runAll(document, config);
  const path = "draft.md";
  const report = JSON.parse(renderJson(new Map([[path, findings]]), null,
    new Map([[path, document.register]]), config.preset, config.exemplars,
    new Map([[path, document]]), config.patches, config.operations, config.protectedTerms));
  return { findings, report: report.files[0], document: fingerprintDict(document) };
}

/** 사람 수정 전후에서 승인할 후보를 추출한다. 후보 자체는 승인이 아니다. @param {string} before @param {string} after @param {import("./config/settings.js").Config} config */
export function learnText(before, after, config = defaultConfig()) {
  const beforeDoc = fingerprint(before, config), afterDoc = fingerprint(after, config);
  return {
    exemplars: learnExemplars(beforeDoc, afterDoc, runAll(beforeDoc, config), runAll(afterDoc, config), config.preset),
    operations: learnOperations(beforeDoc, afterDoc, config.preset, config.protectedTerms),
  };
}

/** 자유 원고의 표면과 H2 순서를 비교한다. 빈 글과 반복 제목도 관찰하며 승인 계약을 만들지 않는다. @param {string} before @param {string} after @param {import("./config/settings.js").Config} config */
export function compareRevision(before, after, config = defaultConfig()) {
  const original = before.normalize("NFC");
  const outline = { level: 2, headings: headingsOf(parseMarkdown(original), 2).map((heading) => heading.text) };
  return { surface: protectedSurface(original), changes: surfaceDiff(original, after),
    outline: compareOutline(outline, fingerprint(after, config)) };
}
