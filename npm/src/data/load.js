// @ts-check
/**
 * data 폴더를 읽는다. 파이썬 정본의 투영이라 파일 모양이 같다. txt 는 한 줄에 항목 하나, json 은 toml 을 옮긴 것.
 * 한 번 읽은 것은 기억한다.
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { compile } from "../regex.js";

const DATA_DIR = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "data");
/** @type {Map<string, unknown>} */
const cache = new Map();

/**
 * @template T
 * @param {string} key
 * @param {() => T} make
 * @returns {T}
 */
function cached(key, make) {
  if (!cache.has(key)) cache.set(key, make());
  return /** @type {T} */ (cache.get(key));
}

/** @param {string} name */
export function readText(name) {
  return readFileSync(join(DATA_DIR, name), "utf-8");
}

/** `#` 으로 시작하면 주석, 빈 줄은 무시. @param {string} name @returns {string[]} */
export function loadLines(name) {
  return cached(`lines:${name}`, () =>
    readText(name)
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#")),
  );
}

/** 한 줄에 정규식 하나. @param {string} name */
export function loadPatterns(name) {
  return cached(`patterns:${name}`, () => loadLines(name).map((line) => compile(line)));
}

/** toml 의 `[[entry]]` 목록. @param {string} name @returns {Record<string, unknown>[]} */
export function loadEntries(name) {
  return cached(`entries:${name}`, () => {
    const data = JSON.parse(readText(name.replace(/\.toml$/, ".json")));
    return data.entry ?? [];
  });
}

/** @returns {Record<string, string>} 규칙 이름 → 기술서 (파이썬 docstring 의 투영) */
export function loadRuleDocs() {
  return cached("ruleDocs", () => JSON.parse(readText("ruleDocs.json")));
}

/** @returns {Record<string, string>} 규칙 이름 → 부류 (규칙 파일이 사는 폴더의 투영) */
export function loadRuleCategories() {
  return cached("ruleCategories", () => JSON.parse(readText("ruleCategories.json")));
}

/** @returns {Record<string, string>} 규칙 이름 → 기제 (파이썬 등록부의 투영) */
export function loadRuleMechanisms() {
  return cached("ruleMechanisms", () => JSON.parse(readText("ruleMechanisms.json")));
}

/** @returns {string} */
export function loadVersion() {
  return cached("version", () => JSON.parse(readText("version.json")).version);
}
