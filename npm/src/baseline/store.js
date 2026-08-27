// @ts-check
/**
 * 이미 있는 지적을 잠가 두고 새로 생긴 것만 막는다. 파이썬 `hanlint/baseline/store.py` 의 투영이다.
 * 왜 줄 번호가 아니라 글자인지, 왜 사람이 읽는 꼴인지는 그 파일의 docstring 이 정본이다.
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, posix, relative, resolve, sep } from "node:path";

/** 기본 파일 이름. 저장소에 커밋해서 팀이 함께 본다. */
export const DEFAULT_NAME = ".hanlint-baseline.json";
export const VERSION = 1;

/** 줄바꿈과 이어진 공백을 하나로 눕힌다. @param {string} quote */
export function normalizeQuote(quote) {
  return quote.split(/\s+/).filter(Boolean).join(" ");
}

/** @param {import("../rules/finding.js").Finding} finding */
export function keyOf(finding) {
  return `${finding.rule}\u0000${normalizeQuote(finding.quote)}`;
}

/** 잠금 파일이 있는 폴더 기준의 상대 경로. @param {string} path @param {string | null} target */
export function pathKey(path, target) {
  if (!target || !path || path.startsWith("<")) return path;
  return relative(dirname(resolve(target)), resolve(path)).split(sep).join(posix.sep);
}

export class Baseline {
  /** @param {Map<string, Set<string>>} [locked] @param {string | null} [source] */
  constructor(locked = new Map(), source = null) {
    this.locked = locked;
    this.source = source;
  }

  get count() {
    let total = 0;
    for (const entries of this.locked.values()) total += entries.size;
    return total;
  }

  /** @param {string} path @param {import("../rules/finding.js").Finding} finding */
  isLocked(path, finding) {
    return (this.locked.get(pathKey(path, this.source)) ?? new Set()).has(keyOf(finding));
  }

  /** 잠기지 않은 지적만 남긴다. @param {string} path @param {import("../rules/finding.js").Finding[]} findings */
  keep(path, findings) {
    return findings.filter((finding) => !this.isLocked(path, finding));
  }
}

/** @param {Map<string, import("../rules/finding.js").Finding[]>} results @param {string | null} [target] */
export function build(results, target = null) {
  /** @type {Map<string, Set<string>>} */
  const locked = new Map();
  for (const [path, findings] of results) {
    if (findings.length) locked.set(pathKey(path, target), new Set(findings.map(keyOf)));
  }
  return new Baseline(locked, target ? resolve(target) : null);
}

/** 사람이 읽고 리뷰하는 꼴. 정렬해 담아 같은 입력에 같은 파일이 나온다. @param {Baseline} baseline */
export function render(baseline) {
  /** @type {Record<string, {rule: string, quote: string}[]>} */
  const files = {};
  let locked = 0;
  for (const path of [...baseline.locked.keys()].sort()) {
    const entries = [...(baseline.locked.get(path) ?? [])].sort();
    if (!entries.length) continue;
    files[path] = entries.map((entry) => {
      const [rule, quote] = entry.split("\u0000");
      return { rule, quote };
    });
    locked += entries.length;
  }
  return JSON.stringify({ version: VERSION, locked, files }, null, 2);
}

/** @param {string} text @param {string | null} [source] */
export function parse(text, source = null) {
  const data = JSON.parse(text);
  if (data.version !== VERSION) throw new Error(`모르는 baseline 판 ${data.version}. hanlint baseline 으로 다시 만든다`);
  /** @type {Map<string, Set<string>>} */
  const locked = new Map();
  for (const [path, entries] of Object.entries(data.files ?? {})) {
    locked.set(path, new Set(/** @type {{rule: string, quote: string}[]} */ (entries).map((e) => `${e.rule}\u0000${e.quote}`)));
  }
  return new Baseline(locked, source);
}

/** @param {string} path */
export function load(path) {
  if (!existsSync(path)) {
    const error = /** @type {NodeJS.ErrnoException} */ (new Error(`${path} 를 찾지 못했다`));
    error.code = "ENOENT";
    error.path = path;
    throw error;
  }
  return parse(readFileSync(path, "utf-8"), resolve(path));
}

/** 지금 글에 더 없는 잠금을 지운다. @param {Baseline} baseline @param {Map<string, import("../rules/finding.js").Finding[]>} results */
export function prune(baseline, results) {
  const kept = new Map(baseline.locked);
  for (const [path, findings] of results) {
    const key = pathKey(path, baseline.source);
    const present = new Set(findings.map(keyOf));
    const remaining = new Set([...(kept.get(key) ?? [])].filter((entry) => present.has(entry)));
    if (remaining.size) kept.set(key, remaining);
    else kept.delete(key);
  }
  return new Baseline(kept, baseline.source);
}
