// @ts-check
/**
 * 명사 연쇄 빈도표. 글 종류마다 data/usageCounts.<종류>.json 하나이고 값은 그 연쇄가 나온 문서 수다.
 * 뜻은 파이썬 usage/counts.py 가 소유한다. 표의 키는 nounRuns 의 어절들을 빈칸 하나로 이은 것이다.
 */
import { USAGE_OF } from "../config/settings.js";
import { readText } from "../data/load.js";

/** @typedef {{ kind: string, source: string, documents: number, minLength: number, minDocuments: number, chains: Record<string, number> }} UsageTable */

/** @type {Map<string, UsageTable>} */
const tables = new Map();

/**
 * 이 설정이 볼 빈도표의 종류. usageKind 가 null 이면 프리셋이 정하고 "" 면 보지 않는다.
 * @param {import("../config/settings.js").Config} config @returns {string | null}
 */
export function usageKindOf(config) {
  const kind = config.usageKind === null ? USAGE_OF[config.preset] : config.usageKind;
  return kind || null;
}

/** 표 전체. @param {string} kind @returns {UsageTable} */
export function usageTable(kind) {
  let table = tables.get(kind);
  if (!table) {
    table = JSON.parse(readText(`usageCounts.${kind}.json`));
    tables.set(kind, /** @type {UsageTable} */ (table));
  }
  return /** @type {UsageTable} */ (table);
}

/** 이 연쇄가 그 종류의 말뭉치에서 몇 편의 문서에 나왔나. 표에 없으면 0. @param {string[]} chain @param {string} kind */
export function chainDocuments(chain, kind) {
  return usageTable(kind).chains[chain.join(" ")] ?? 0;
}

/** 연쇄가 minimum 편 이상의 문서에 나왔으면 그 종류의 관용이다. @param {string[]} chain @param {string} kind @param {number} minimum */
export function attested(chain, kind, minimum) {
  return chainDocuments(chain, kind) >= minimum;
}
