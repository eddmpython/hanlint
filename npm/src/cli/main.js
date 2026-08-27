// @ts-check
/**
 * 명령줄 진입점. 파이썬 CLI 와 같은 인자, 같은 출력, 같은 종료 코드다 (0 지적 없음, 1 error 있음, 2 파일이나 설정 문제).
 *
 * ```
 * hanlint 글.md [다른.md ...]   검사. 서브커맨드 없이 파일만 주면 lint 다. `-` 는 stdin
 * hanlint fix 글.md             기계가 고칠 수 있는 지적을 원문에 적용
 * hanlint print 글.md           지문 계층 JSON
 * hanlint rules                 규칙 목록
 * hanlint explain <규칙>        규칙의 기술서
 * hanlint init                  주석 달린 hanlint.toml
 * ```
 * audit, map, profile 과 kiwi 정밀 모드는 파이썬 패키지 (pip install hanlint) 에 있다.
 */
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, relative, resolve } from "node:path";

import { analyzerFor, fingerprint, lintText, ruleDoc, ruleNames, ruleSummary, version } from "../index.js";
import { loadConfig } from "../config/loadConfig.js";
import { defaultConfig } from "../config/settings.js";
import { applyFixes } from "../edit/applyFixes.js";
import { runAll } from "../rules/registry.js";
import { renderCompact } from "../report/compactReport.js";
import { LAYERS, renderFingerprintJson } from "../report/fingerprintJson.js";
import { renderGithub } from "../report/githubReport.js";
import { renderJson } from "../report/jsonReport.js";
import { renderText } from "../report/textReport.js";

const COMMANDS = ["lint", "fix", "print", "rules", "explain", "init"];
const PYTHON_ONLY = ["audit", "map", "profile"];
const FORMATS = ["text", "compact", "json", "github"];
const SEVERITIES = ["all", "error", "notice"];
const ANALYZER_CHOICES = ["surface", "kiwi"];
const STDIN = "-";
const STDIN_NAME = "<stdin>";
const THRESHOLD_FIELDS = [
  "fragmentRun",
  "introMaxParagraphs",
  "headingUniformRatio",
  "nounPileMin",
  "endingRun",
  "factListMinSentences",
  "factListMaxMeanLength",
  "topicBreakMinSentences",
  "longSentenceMax",
];
const FLOAT_FIELDS = new Set(["headingUniformRatio", "factListMaxMeanLength"]);

const USAGE = `사용법: hanlint 글.md [다른.md ...] [--format text|compact|json|github] [--severity all|error|notice] [--errors-only]
                [--config 파일] [--disable 규칙] [--output 파일] [--quiet] [--path 이름 (stdin 의 이름)]
        hanlint fix 글.md [--dry-run]
        hanlint print 글.md [--layer all|sentences|paragraphs|sections|document]
        hanlint rules [--names]
        hanlint explain <규칙>
        hanlint init [--path hanlint.toml] [--force]
        hanlint --version

한국어 글에서 반복되는 결함을 결정적으로 잡는다. 종료 코드는 0 (지적 없음), 1 (error 지적), 2 (파일이나 설정 문제).
audit, map, profile 과 kiwi 정밀 모드는 파이썬 패키지 (pip install hanlint) 에 있다.`;

/** @type {Record<string, "value" | "list" | "flag">} */
const OPTION_KINDS = {
  "--format": "value",
  "--config": "value",
  "--disable": "list",
  "--analyzer": "value",
  "--output": "value",
  "--no-color": "flag",
  "--quiet": "flag",
  "--severity": "value",
  "--errors-only": "flag",
  "--path": "value",
  "--layer": "value",
  "--dry-run": "flag",
  "--names": "flag",
  "--force": "flag",
};

class UsageError extends Error {}

/**
 * @param {string[]} args
 * @returns {{ options: Record<string, string | string[] | boolean>, positionals: string[] }}
 */
function parseArgs(args) {
  /** @type {Record<string, string | string[] | boolean>} */
  const options = {};
  /** @type {string[]} */
  const positionals = [];
  for (let i = 0; i < args.length; i++) {
    let arg = args[i];
    if (!arg.startsWith("--")) {
      positionals.push(arg);
      continue;
    }
    let inlineValue = null;
    const eq = arg.indexOf("=");
    if (eq > 0) {
      inlineValue = arg.slice(eq + 1);
      arg = arg.slice(0, eq);
    }
    const kind = OPTION_KINDS[arg];
    if (!kind) throw new UsageError(`모르는 옵션: ${arg}`);
    if (kind === "flag") {
      options[arg] = true;
      continue;
    }
    const value = inlineValue ?? args[++i];
    if (value === undefined) throw new UsageError(`${arg} 에 값이 없다`);
    if (kind === "list") {
      const list = /** @type {string[]} */ (options[arg] ?? []);
      list.push(value);
      options[arg] = list;
    } else {
      options[arg] = value;
    }
  }
  return { options, positionals };
}

/** 서브커맨드 없이 파일이나 옵션만 주면 lint 로 본다. @param {string[]} argv */
export function normalizeArgv(argv) {
  if (!argv.length) return ["lint"];
  if (COMMANDS.includes(argv[0]) || PYTHON_ONLY.includes(argv[0]) || ["-h", "--help", "--version"].includes(argv[0])) return argv;
  return ["lint", ...argv];
}

/** @param {string} value @param {string[]} choices @param {string} option */
function choose(value, choices, option) {
  if (!choices.includes(value)) throw new UsageError(`${option} 는 ${choices.join(", ")} 가운데 하나다: ${value}`);
  return value;
}

/** @param {string} text @param {string | undefined} output */
function emit(text, output) {
  if (output === undefined) {
    process.stdout.write(`${text}\n`);
    return;
  }
  writeFileSync(output, text.endsWith("\n") ? text : `${text}\n`, "utf-8");
  process.stderr.write(`${output} 에 썼다\n`);
}

/** 설정을 찾기 시작할 폴더. 첫 실제 파일의 폴더, 전부 stdin 이면 현재 폴더. @param {string[]} paths */
function startFolder(paths) {
  for (const path of paths) if (path !== STDIN) return dirname(resolve(path));
  return process.cwd();
}

/** @param {Record<string, string | string[] | boolean>} options @param {string[]} paths */
function configFrom(options, paths) {
  const config = loadConfig(/** @type {string | undefined} */ (options["--config"]) ?? null, startFolder(paths));
  for (const rule of /** @type {string[]} */ (options["--disable"] ?? [])) config.disable.add(rule);
  if (options["--analyzer"]) config.analyzer = choose(/** @type {string} */ (options["--analyzer"]), ANALYZER_CHOICES, "--analyzer");
  return config;
}

/** 출력 첫 줄에 적을 설정 출처. 현재 폴더 아래면 상대 경로, 아니면 그대로. @param {import("../config/settings.js").Config} config */
function configLabel(config) {
  if (config.source === null) return "기본값";
  const rel = relative(process.cwd(), config.source);
  if (!rel || rel.startsWith("..") || isAbsolute(rel)) return config.source;
  return rel;
}

/** @param {Map<string, import("../rules/finding.js").Finding[]>} results */
function summary(results) {
  let errors = 0;
  let notices = 0;
  for (const findings of results.values()) {
    for (const f of findings) {
      if (f.severity === "error") errors += 1;
      else if (f.severity === "notice") notices += 1;
    }
  }
  return `파일 ${results.size}개, error ${errors}, notice ${notices}`;
}

/** (이름, 본문). `-` 면 stdin 을 UTF-8 로 읽는다. @param {string} path @param {string} stdinName @returns {[string, string]} */
function readInput(path, stdinName) {
  if (path === STDIN) return [stdinName, readFileSync(0, "utf-8")];
  return [path, readFileSync(path, "utf-8")];
}

/** @param {string[]} args */
function runLint(args) {
  const { options, positionals } = parseArgs(args);
  if (!positionals.length) throw new UsageError("검사할 마크다운 파일이 필요하다");
  const format = choose(/** @type {string} */ (options["--format"] ?? "text"), FORMATS, "--format");
  const severity = options["--errors-only"] ? "error" : choose(/** @type {string} */ (options["--severity"] ?? "all"), SEVERITIES, "--severity");
  const config = configFrom(options, positionals);
  analyzerFor(config);
  const stdinName = /** @type {string} */ (options["--path"] ?? STDIN_NAME);
  /** @type {Map<string, import("../rules/finding.js").Finding[]>} */
  const results = new Map();
  for (const path of positionals) {
    const [name, text] = readInput(path, stdinName);
    results.set(name, lintText(text, config, name));
  }
  const hasError = [...results.values()].some((findings) => findings.some((f) => f.severity === "error"));
  /** @type {Map<string, import("../rules/finding.js").Finding[]>} */
  const shown = new Map();
  for (const [name, findings] of results) shown.set(name, severity === "all" ? findings : findings.filter((f) => f.severity === severity));

  const output = /** @type {string | undefined} */ (options["--output"]);
  if (format === "json") {
    emit(renderJson(shown, configLabel(config)), output);
  } else if (format === "github") {
    emit([...shown].map(([name, findings]) => renderGithub(name, findings)).join("\n"), output);
  } else {
    const parts = [];
    if (!options["--quiet"]) parts.push(`설정: ${configLabel(config)}`);
    if (format === "compact") {
      const body = [...shown]
        .filter(([, findings]) => findings.length)
        .map(([name, findings]) => renderCompact(name, findings))
        .join("\n");
      if (body) parts.push(body);
      parts.push(summary(shown));
      emit(parts.join("\n"), output);
    } else {
      parts.push([...shown].map(([name, findings]) => renderText(name, findings)).join("\n\n"));
      if (shown.size > 1) parts.push(summary(shown));
      emit(parts.join("\n\n"), output);
    }
  }
  return hasError ? 1 : 0;
}

/** @param {string[]} args */
function runFix(args) {
  const { options, positionals } = parseArgs(args);
  if (!positionals.length) throw new UsageError("고칠 마크다운 파일이 필요하다");
  const config = configFrom(options, positionals);
  const analyzer = analyzerFor(config);
  void analyzer;
  const lines = [];
  for (const path of positionals) {
    const text = readFileSync(path, "utf-8");
    // notice 는 제안이라 손으로 정한다. 확정된 error 만 원문에 넣는다.
    const result = applyFixes(
      text,
      runAll(fingerprint(text, config, path), config).filter((f) => f.severity === "error"),
    );
    for (const [line, fragment, replacement] of result.applied) lines.push(`${path}:${line}  ${fragment} → ${replacement}`);
    for (const [line, fragment, reason] of result.skipped) lines.push(`${path}:${line}  건너뜀 ${fragment}: ${reason}`);
    if (result.text !== text && !options["--dry-run"]) writeFileSync(path, result.text, "utf-8");
    lines.push(`${path}  ${result.applied.length}곳 고침, ${result.skipped.length}곳 건너뜀` + (options["--dry-run"] ? " (미리보기, 파일은 그대로)" : ""));
  }
  process.stdout.write(`${lines.join("\n")}\n`);
  return 0;
}

/** @param {string[]} args */
function runPrint(args) {
  const { options, positionals } = parseArgs(args);
  if (positionals.length !== 1) throw new UsageError("마크다운 파일 하나가 필요하다. `-` 는 stdin");
  const layer = choose(/** @type {string} */ (options["--layer"] ?? "all"), LAYERS, "--layer");
  const config = configFrom(options, positionals);
  const [name, text] = readInput(positionals[0], /** @type {string} */ (options["--path"] ?? STDIN_NAME));
  emit(renderFingerprintJson(fingerprint(text, config, name), layer), /** @type {string | undefined} */ (options["--output"]));
  return 0;
}

/** @param {string[]} args */
function runRules(args) {
  const { options } = parseArgs(args);
  const names = ruleNames();
  if (options["--names"]) {
    process.stdout.write(`${names.join("\n")}\n`);
    return 0;
  }
  const width = Math.max(...names.map((name) => name.length));
  const lines = names.map((name) => `${name.padEnd(width)}  ${ruleSummary(name)}`);
  process.stdout.write(`${lines.join("\n")}\n\n규칙 ${names.length}개. 자세히 보려면 hanlint explain <규칙>\n`);
  return 0;
}

/** @param {string[]} args */
function runExplain(args) {
  const { positionals } = parseArgs(args);
  if (positionals.length !== 1) throw new UsageError("규칙 이름 하나가 필요하다. hanlint rules 로 목록을 본다");
  const doc = ruleDoc(positionals[0]);
  process.stdout.write(`${positionals[0]}\n\n${doc}\n`);
  return 0;
}

/** 주석 달린 hanlint.toml. 파이썬 `hanlint init` 과 같은 글자다. */
export function renderInit() {
  const defaults = defaultConfig();
  const lines = ["# hanlint 설정. 규칙을 끄려면 disable 에 이름을 넣는다. 규칙의 기술서는 hanlint explain <규칙>.", "", "# 규칙 목록과 한 줄 설명"];
  for (const name of ruleNames()) lines.push(`#   ${name}: ${ruleSummary(name)}`);
  lines.push(
    "",
    "disable = []",
    "",
    "# surface 는 의존성 0 기본, kiwi 는 pip install hanlint[kiwi] 가 있을 때",
    `analyzer = "${defaults.analyzer}"`,
    "",
    "# 대표 검색어를 읽을 frontmatter 필드. 없으면 keywordMissing 은 돌지 않는다",
    '# keywordField = "primaryKeyword"',
    "",
    "# hanlint profile build 가 만든 파일. 있으면 참조 글과의 편차 구간을 notice 로 더한다",
    '# profile = "profile.json"',
    "",
    "# 임계. 기본값의 정본은 hanlint 의 config/settings.py 다",
  );
  for (const name of THRESHOLD_FIELDS) {
    const value = /** @type {number} */ (defaults[name]);
    const shown = FLOAT_FIELDS.has(name) && Number.isInteger(value) ? value.toFixed(1) : String(value);
    lines.push(`# ${name} = ${shown}`);
  }
  lines.push(
    "",
    "# 사전에 더할 항목. 키는 cliches, translationese, redundantPair, japaneseLoan",
    "# [dictionary]",
    '# cliches = ["우리의 여정"]',
    '# translationese = [{ pattern = "에 대한 이해", fix = "를 아는 것" }]',
    "",
  );
  return lines.join("\n");
}

/** @param {string[]} args */
function runInit(args) {
  const { options } = parseArgs(args);
  const path = /** @type {string} */ (options["--path"] ?? "hanlint.toml");
  if (existsSync(path) && !options["--force"]) throw new Error(`${path} 가 이미 있다. 덮어쓰려면 --force`);
  writeFileSync(path, renderInit(), "utf-8");
  process.stdout.write(`${path} 를 만들었다. 규칙을 끄려면 disable 에 이름을 넣는다\n`);
  return 0;
}

/** @param {string[]} argv */
function dispatch(argv) {
  const [command, ...rest] = normalizeArgv(argv);
  if (command === "-h" || command === "--help") {
    process.stdout.write(`${USAGE}\n`);
    return 0;
  }
  if (command === "--version") {
    process.stdout.write(`hanlint ${version}\n`);
    return 0;
  }
  if (PYTHON_ONLY.includes(command)) {
    throw new Error(`${command} 는 파이썬 패키지에 있다 (pip install hanlint). npm 은 lint, fix, print, rules, explain, init 을 제공한다`);
  }
  if (command === "lint") return runLint(rest);
  if (command === "fix") return runFix(rest);
  if (command === "print") return runPrint(rest);
  if (command === "rules") return runRules(rest);
  if (command === "explain") return runExplain(rest);
  return runInit(rest);
}

/** @param {string[]} argv @returns {number} */
export function main(argv) {
  try {
    return dispatch(argv);
  } catch (error) {
    if (error instanceof UsageError) {
      process.stderr.write(`${error.message}\n\n${USAGE}\n`);
      return 2;
    }
    const failure = /** @type {NodeJS.ErrnoException} */ (error);
    if (failure.code === "ENOENT") {
      process.stderr.write(`${failure.path} 를 찾지 못했다. 경로를 확인하거나 hanlint --help\n`);
      return 2;
    }
    process.stderr.write(`${failure.message}\n`);
    return 2;
  }
}
