// @ts-check
/**
 * 명령줄 진입점. 파이썬 CLI 와 같은 인자, 같은 출력, 같은 종료 코드다 (0 지적 없음, 1 error 있음, 2 파일이나 설정 문제).
 *
 * ```
 * hanlint 글.md [다른.md ...]   검사. 서브커맨드 없이 파일만 주면 lint 다
 * hanlint rules                 규칙 목록
 * hanlint explain <규칙>        규칙의 기술서
 * hanlint init                  주석 달린 hanlint.toml
 * ```
 * audit, map, print, profile 과 kiwi 정밀 모드는 파이썬 패키지 (pip install hanlint) 에 있다.
 */
import { existsSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

import { analyzerFor, lintText, ruleDoc, ruleNames, ruleSummary, version } from "../index.js";
import { loadConfig } from "../config/loadConfig.js";
import { defaultConfig } from "../config/settings.js";
import { readFileSync } from "node:fs";
import { renderGithub } from "../report/githubReport.js";
import { renderJson } from "../report/jsonReport.js";
import { renderText } from "../report/textReport.js";

const COMMANDS = ["lint", "rules", "explain", "init"];
const PYTHON_ONLY = ["audit", "map", "print", "profile"];
const FORMATS = ["text", "json", "github"];
const ANALYZER_CHOICES = ["surface", "kiwi"];
const THRESHOLD_FIELDS = [
  "fragmentRun",
  "introMaxParagraphs",
  "headingUniformRatio",
  "nounPileMin",
  "endingRun",
  "factListMinSentences",
  "factListMaxMeanLength",
  "topicBreakMinSentences",
];
const FLOAT_FIELDS = new Set(["headingUniformRatio", "factListMaxMeanLength"]);

const USAGE = `사용법: hanlint 글.md [다른.md ...] [--format text|json|github] [--config 파일] [--disable 규칙] [--output 파일]
        hanlint rules [--names]
        hanlint explain <규칙>
        hanlint init [--path hanlint.toml] [--force]
        hanlint --version

한국어 글에서 반복되는 결함을 결정적으로 잡는다. 종료 코드는 0 (지적 없음), 1 (error 지적), 2 (파일이나 설정 문제).
audit, map, print, profile 과 kiwi 정밀 모드는 파이썬 패키지 (pip install hanlint) 에 있다.`;

/** @type {Record<string, "value" | "list" | "flag">} */
const OPTION_KINDS = {
  "--format": "value",
  "--config": "value",
  "--disable": "list",
  "--analyzer": "value",
  "--output": "value",
  "--no-color": "flag",
  "--names": "flag",
  "--path": "value",
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

/** @param {string[]} args */
function runLint(args) {
  const { options, positionals } = parseArgs(args);
  if (!positionals.length) throw new UsageError("검사할 마크다운 파일이 필요하다");
  const format = choose(/** @type {string} */ (options["--format"] ?? "text"), FORMATS, "--format");
  const config = loadConfig(/** @type {string | undefined} */ (options["--config"]) ?? null, dirname(resolve(positionals[0])));
  for (const rule of /** @type {string[]} */ (options["--disable"] ?? [])) config.disable.add(rule);
  if (options["--analyzer"]) config.analyzer = choose(/** @type {string} */ (options["--analyzer"]), ANALYZER_CHOICES, "--analyzer");
  const analyzer = analyzerFor(config);
  void analyzer;
  /** @type {Map<string, import("../rules/finding.js").Finding[]>} */
  const results = new Map();
  for (const path of positionals) {
    results.set(path, lintText(readFileSync(path, "utf-8"), config, path));
  }
  const output = /** @type {string | undefined} */ (options["--output"]);
  if (format === "json") emit(renderJson(results), output);
  else if (format === "github") emit([...results].map(([path, findings]) => renderGithub(path, findings)).join("\n"), output);
  else emit([...results].map(([path, findings]) => renderText(path, findings)).join("\n\n"), output);
  const hasError = [...results.values()].some((findings) => findings.some((f) => f.severity === "error"));
  return hasError ? 1 : 0;
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
    throw new Error(`${command} 는 파이썬 패키지에 있다 (pip install hanlint). npm 은 lint, rules, explain, init 을 제공한다`);
  }
  if (command === "lint") return runLint(rest);
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
