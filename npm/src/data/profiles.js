// @ts-check
/**
 * 참조 분포 (프로파일) 의 자료형과 읽기. 파이썬 data/profiles.py 와 같다. 종류별 프로파일은 profiles.json (투영) 에서,
 * 사용자 프로파일은 `hanlint profile build` 가 만든 파일에서 읽는다. 히스토그램은 정확한 계수라 두 판의 셈이 같다.
 */
import { readFileSync } from "node:fs";

import { readText } from "./load.js";

export const PROFILE_VERSION = 1;
/** 히스토그램의 상한. 이 값보다 큰 것은 상한에 합친다. */
export const CAP = 200;
const PERCENTILES = [50, 90, 95, 99];
/** 기준 말뭉치 종류의 이름. 지적문에 적는다. 파이썬 TYPE_LABELS 와 같다. @type {Record<string, string>} */
export const TYPE_LABELS = {
  blog: "블로그",
  technicalDocs: "기술 문서",
  guide: "안내서",
  report: "뉴스와 보고문",
  essay: "수필 (1930년대)",
  fiction: "소설 (1930년대)",
  encyclopedia: "백과",
};

/**
 * @typedef {object} Histogram
 * @property {number} total
 * @property {Map<number, number>} counts 값 → 수
 * @property {Map<number, number>} percentiles 백분위 → 값
 */

/**
 * @typedef {object} Profile
 * @property {string} kind
 * @property {number} documents
 * @property {number} sentences
 * @property {number} paragraphs
 * @property {Map<string, Histogram>} sentence
 * @property {string} label
 */

/** @param {Record<string, unknown>} data @returns {Histogram} */
function histogramFromDict(data) {
  const counts = new Map();
  for (const [value, count] of Object.entries(/** @type {Record<string, number>} */ (data.counts))) counts.set(Number(value), Number(count));
  const percentiles = new Map();
  for (const p of PERCENTILES) if (`p${p}` in data) percentiles.set(p, Number(data[`p${p}`]));
  return { total: Number(data.total), counts, percentiles };
}

/** 값이 이 이상인 것의 몫을 천분율 정수로. 정수 셈이라 두 판의 글자가 같다. @param {Histogram} hist @param {number} value */
export function shareAtOrAbove(hist, value) {
  const capped = Math.min(value, CAP);
  let above = 0;
  for (const [seen, count] of hist.counts) if (seen >= capped) above += count;
  return hist.total ? Math.floor((above * 1000) / hist.total) : 0;
}

/** @param {string} kind @param {Record<string, unknown>} data @returns {Profile} */
function profileFromDict(kind, data) {
  const sentence = new Map();
  for (const [name, value] of Object.entries(/** @type {Record<string, Record<string, unknown>>} */ (data.sentence))) {
    sentence.set(name, histogramFromDict(value));
  }
  const documents = Number(data.documents);
  return {
    kind,
    documents,
    sentences: Number(data.sentences),
    paragraphs: Number(data.paragraphs),
    sentence,
    label: TYPE_LABELS[kind] ?? `참조 글 ${documents}편`,
  };
}

/** @type {Map<string, Profile> | null} */
let shipped = null;
/** hanlint 가 싣는 종류별 프로파일. @param {string} kind @returns {Profile | null} */
export function profileOf(kind) {
  if (!shipped) {
    shipped = new Map();
    const data = JSON.parse(readText("profiles.json"));
    for (const [name, value] of Object.entries(data.types)) shipped.set(name, profileFromDict(name, value));
  }
  return shipped.get(kind) ?? null;
}

/** @type {Map<string, Profile>} */
const users = new Map();
/** 사용자 프로파일 파일. 한 번 읽은 것은 기억한다. @param {string} path @returns {Profile} */
export function userProfile(path) {
  let profile = users.get(path);
  if (!profile) {
    const data = JSON.parse(readFileSync(path, "utf-8"));
    if (data.version !== PROFILE_VERSION || !("profile" in data)) {
      throw new Error(`프로파일 파일이 아니다: ${path}. hanlint profile build 로 다시 만든다`);
    }
    profile = profileFromDict("custom", data.profile);
    users.set(path, profile);
  }
  return profile;
}
