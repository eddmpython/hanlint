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
 * 지문 지도 (audit, map) 와 프로파일은 파이썬 패키지에 있다.
 */
import { readFileSync } from "node:fs";

import { loadConfig } from "./config/loadConfig.js";
import { Contract, Patch } from "./config/readerContract.js";
import { configFromMapping, defaultConfig } from "./config/settings.js";
import { loadVersion } from "./data/load.js";
import { parseMarkdown } from "./document/parseMarkdown.js";
import { applyFixes } from "./edit/applyFixes.js";
import { buildFingerprint } from "./fingerprint/build.js";
import { fingerprintDict } from "./report/fingerprintJson.js";
import { CheckResult, PatchResult, check, verifyPatch } from "./guard/contract.js";
import { ruleDoc, ruleNames, ruleSummary, runAll } from "./rules/registry.js";

export {
  CheckResult,
  Contract,
  Patch,
  PatchResult,
  applyFixes,
  check,
  configFromMapping,
  defaultConfig,
  fingerprintDict,
  loadConfig,
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
  return lintText(readFileSync(path, "utf-8"), config, path);
}
