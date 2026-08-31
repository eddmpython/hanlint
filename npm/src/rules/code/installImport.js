// @ts-check
import { loadLines } from "../../data/load.js";
import { DOCUMENT, NOTICE, finding } from "../finding.js";

export const name = "installImport";
export const mechanism = "contrast";

// 캡처는 백틱과 한글에서 멈춘다. 안 멈추면 설치 줄 뒤의 산문을 패키지로 등록한다. 파이썬과 같다.
const INSTALL = /(?:pip\s+install|uv\s+add|uv\s+pip\s+install|conda\s+install|poetry\s+add)\s+([^\n#|&;`가-힣]+)/g;
const IMPORT = /^\s*(?:import\s+([\w.]+(?:\s*,\s*[\w.]+)*)|from\s+([\w.]+)\s+import\b)/;
const REQUIREMENT = /^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[([^\]]*)\])?/;
const PY_FILE = /\b(\w+)\.py\b/g;

/** @type {Set<string> | null} */
let stdlibCache = null;
function stdlib() {
  if (!stdlibCache) stdlibCache = new Set(loadLines("pythonStdlib.txt"));
  return stdlibCache;
}

/** @type {Map<string, string> | null} */
let packageCache = null;
function packageOf() {
  if (!packageCache) {
    packageCache = new Map();
    for (const line of loadLines("pythonPackages.txt")) {
      const [module, pkg] = line.split("\t");
      packageCache.set(module, pkg);
    }
  }
  return packageCache;
}

/** @type {[RegExp, string, string][] | null} */
let hiddenCache = null;
function hiddenDeps() {
  if (!hiddenCache) {
    hiddenCache = loadLines("hiddenDeps.txt").map((line) => {
      const [pattern, requirement, why] = line.split("\t");
      return /** @type {[RegExp, string, string]} */ ([new RegExp(pattern), requirement, why]);
    });
  }
  return hiddenCache;
}

/** @param {string} value */
function normalize(value) {
  return value.toLowerCase().replace(/_/g, "-");
}

/** 설치 줄이 말한 패키지 → extras. 설치 줄이 하나도 없으면 null. @param {import("../../fingerprint/build.js").DocumentPrint} doc */
function installed(doc) {
  const texts = [...doc.codeBlocks.flatMap((b) => b.lines.map(([, line]) => line)), ...doc.sentences.map((s) => s.text)];
  /** @type {Map<string, Set<string>>} */
  const packages = new Map();
  let seen = false;
  for (const text of texts) {
    INSTALL.lastIndex = 0;
    for (const match of text.matchAll(INSTALL)) {
      seen = true;
      for (let token of match[1].split(/\s+/)) {
        token = token.replace(/^["'`]+|["'`]+$/g, "");
        if (token.startsWith("-") || !token) continue;
        const requirement = REQUIREMENT.exec(token);
        if (!requirement) continue;
        const name2 = normalize(requirement[1]);
        const extras = new Set((requirement[2] ?? "").split(",").map((e) => normalize(e.trim())).filter(Boolean));
        const current = packages.get(name2) ?? new Set();
        for (const extra of extras) current.add(extra);
        packages.set(name2, current);
      }
    }
  }
  return seen ? packages : null;
}

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
function localModules(doc) {
  const names = new Set();
  for (const sentence of doc.sentences) {
    PY_FILE.lastIndex = 0;
    for (const match of sentence.text.matchAll(PY_FILE)) names.add(match[1]);
  }
  for (const block of doc.codeBlocks) {
    for (const [, line] of block.lines) {
      PY_FILE.lastIndex = 0;
      for (const match of line.matchAll(PY_FILE)) names.add(match[1]);
    }
  }
  return names;
}

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const packages = installed(doc);
  if (packages === null) return [];
  const local = localModules(doc);
  const findings = [];
  for (const block of doc.codeBlocks) {
    if (!["python", "py"].includes(block.language)) continue;
    for (const [line, code] of block.lines) {
      const match = IMPORT.exec(code);
      if (match) {
        const modules = (match[1] ?? match[2]).split(",").map((m) => m.trim());
        for (const module of modules) {
          const top = module.split(".")[0];
          if (!top || stdlib().has(top) || local.has(top)) continue;
          const pkg = normalize(packageOf().get(top) ?? top);
          if (!packages.has(pkg)) {
            findings.push(finding(name, line, code.trim(), `\`${top}\` 를 import 하는데 설치 줄에 \`${pkg}\` 가 없다. 독자는 ModuleNotFoundError 에서 멈춘다`, null, "error", DOCUMENT, block.index));
          }
        }
      }
      for (const [pattern, requirement, why] of hiddenDeps()) {
        pattern.lastIndex = 0;
        if (!pattern.test(code)) continue;
        const parsed = REQUIREMENT.exec(requirement);
        if (!parsed) continue;
        const name2 = normalize(parsed[1]);
        const extra = parsed[2] ? normalize(parsed[2]) : null;
        if (packages.has(name2) && (extra === null || (packages.get(name2)?.has(extra) ?? false))) continue;
        findings.push(finding(name, line, code.trim(), `이 줄은 \`${requirement}\` 가 있어야 돈다. ${why}. 설치 줄에 없다`, null, NOTICE, DOCUMENT, block.index));
      }
    }
  }
  return findings;
}
