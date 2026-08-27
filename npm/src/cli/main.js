// @ts-check
/**
 * 명령줄 진입점. 파이썬 CLI 와 같은 인자, 같은 출력, 같은 종료 코드다 (0 지적 없음, 1 error 있음, 2 파일이나 설정 문제).
 *
 * ```
 * hanlint                       인자가 없으면 첫 화면. 무엇을 칠 수 있는지 보인다
 * hanlint 글.md [다른.md ...]   검사. 서브커맨드 없이 파일이나 폴더만 주면 lint 다. `-` 는 stdin
 * hanlint fix 글.md             기계가 고칠 수 있는 지적을 원문에 적용
 * hanlint print 글.md           지문 계층 JSON
 * hanlint rules                 규칙 목록을 부류로 묶어서
 * hanlint explain <규칙>        규칙의 기술서
 * hanlint doctor                설정, 분석기, 꺼진 규칙
 * hanlint init                  주석 달린 hanlint.toml. --preset blog|report|docs
 * ```
 * audit, map, watch, profile 과 kiwi 정밀 모드는 파이썬 패키지 (pip install hanlint) 에 있다.
 */
import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";

import { analyzerFor, fingerprint, lintText, ruleDoc, ruleNames, ruleSummary, version } from "../index.js";
import { loadConfig } from "../config/loadConfig.js";
import { defaultConfig, offRules, PRESET_NAMES, PRESETS } from "../config/settings.js";
import { applyFixes } from "../edit/applyFixes.js";
import { exemplarFor } from "../data/exemplars.js";
import { CATEGORY_TITLES, ruleCategory, runAll } from "../rules/registry.js";
import { welcome } from "./welcome.js";
import { renderCompact } from "../report/compactReport.js";
import { LAYERS, renderFingerprintJson } from "../report/fingerprintJson.js";
import { renderGithub } from "../report/githubReport.js";
import { renderJson } from "../report/jsonReport.js";
import { renderText } from "../report/textReport.js";

const COMMANDS = ["lint", "fix", "print", "rules", "explain", "doctor", "init"];
const PYTHON_ONLY = ["audit", "map", "watch", "profile", "coverage", "diff"];
const FORMATS = ["text", "compact", "json", "github"];
const SEVERITIES = ["all", "error", "notice"];
const ANALYZER_CHOICES = ["surface", "kiwi"];
const STDIN = "-";
const STDIN_NAME = "<stdin>";
/** 폴더를 주면 이 확장자만 찾는다. 파이썬 cli/commands/shared.py 의 MARKDOWN 과 같다. */
const MARKDOWN = [".md", ".markdown"];
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
  "duplicateBlockRatio",
  "firstResultMaxParagraphs",
  "sectionResultMinParagraphs",
  "introMaxImages",
  "headingQuestionRatio",
  "moreLaterMaxChars",
  "tableOddCellMinRows",
];
const FLOAT_FIELDS = new Set(["headingUniformRatio", "factListMaxMeanLength", "headingQuestionRatio"]);

const USAGE = `사용법: hanlint 글.md [다른.md ...] [--format text|compact|json|github] [--severity all|error|notice] [--errors-only]
                [--config 파일] [--disable 규칙] [--output 파일] [--quiet] [--path 이름 (stdin 의 이름)]
        hanlint fix 글.md [--dry-run]
        hanlint print 글.md [--layer all|sentences|paragraphs|sections|document]
        hanlint rules [--names]
        hanlint explain <규칙>
        hanlint doctor
        hanlint init [--path hanlint.toml] [--preset blog|report|docs] [--force]
        hanlint --version

파일 자리에 폴더를 주면 그 아래 마크다운을 전부 검사한다. 인자가 없으면 첫 화면이 나온다.
한국어 글에서 반복되는 결함을 결정적으로 잡는다. 종료 코드는 0 (지적 없음), 1 (error 지적), 2 (파일이나 설정 문제).
audit, map, watch, profile 과 kiwi 정밀 모드는 파이썬 패키지 (pip install hanlint) 에 있다.`;

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
  "--preset": "value",
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

/**
 * 서브커맨드 없이 파일이나 옵션만 주면 lint 로 본다. 빈 인자는 여기서 다루지 않는다. `main` 이 첫 화면으로 보낸다.
 * @param {string[]} argv
 */
export function normalizeArgv(argv) {
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

/** 폴더 안의 마크다운 전부. 부른 쪽이 경로 문자열로 정렬한다 (파이썬 판과 같은 순서). @param {string} folder */
function markdownUnder(folder) {
  /** @type {string[]} */
  const found = [];
  for (const name of readdirSync(folder)) {
    const path = join(folder, name);
    if (statSync(path).isDirectory()) found.push(...markdownUnder(path));
    else if (MARKDOWN.includes(name.slice(name.lastIndexOf(".")).toLowerCase())) found.push(path);
  }
  return found;
}

/** 폴더를 주면 그 아래 마크다운을 편다. 파일과 `-` 는 그대로 둔다. @param {string[]} paths */
function collectFiles(paths) {
  /** @type {string[]} */
  const found = [];
  for (const path of paths) {
    if (path === STDIN) {
      found.push(STDIN);
      continue;
    }
    let isFolder = false;
    try {
      isFolder = statSync(path).isDirectory();
    } catch {
      isFolder = false;
    }
    if (!isFolder) {
      found.push(path);
      continue;
    }
    const inside = markdownUnder(path).sort();
    if (!inside.length) throw new Error(`${path} 안에 마크다운 파일이 없다. 다른 폴더를 주거나 파일을 직접 준다`);
    found.push(...inside);
  }
  return found;
}

/** 검사 끝에 붙는 다음 행동 한 줄. 합격을 판정하지 않고 지금 무엇을 하면 되는지만 말한다.
 * @param {Map<string, import("../rules/finding.js").Finding[]>} results */
function nextStep(results) {
  const findings = [...results.values()].flat();
  const errors = findings.filter((f) => f.severity === "error");
  const notices = findings.length - errors.length;
  const fixable = errors.filter((f) => f.replacement !== null).length;
  if (errors.length) {
    const rule = [...new Set(errors.map((f) => f.rule))].sort()[0];
    if (fixable) return `다음: error ${errors.length}건 가운데 ${fixable}건은 hanlint fix 가 바로 고친다. 나머지는 손으로 고친다`;
    return `다음: error ${errors.length}건을 고친다. 규칙이 왜 있는지는 hanlint explain ${rule}`;
  }
  if (notices) return `다음: error 0. 확인할 자리 ${notices}건을 읽고 판단한 뒤 사람과 LLM 평가로 넘어간다`;
  return "다음: 세어서 잡히는 결함이 없다. 좋은 글이라는 뜻은 아니므로 사람과 LLM 평가로 넘어간다";
}

/** @param {string[]} args */
function runLint(args) {
  const { options, positionals } = parseArgs(args);
  if (!positionals.length) throw new UsageError("검사할 마크다운 파일이 필요하다");
  const files = collectFiles(positionals);
  const format = choose(/** @type {string} */ (options["--format"] ?? "text"), FORMATS, "--format");
  const severity = options["--errors-only"] ? "error" : choose(/** @type {string} */ (options["--severity"] ?? "all"), SEVERITIES, "--severity");
  const config = configFrom(options, files);
  analyzerFor(config);
  const stdinName = /** @type {string} */ (options["--path"] ?? STDIN_NAME);
  /** @type {Map<string, import("../rules/finding.js").Finding[]>} */
  const results = new Map();
  for (const path of files) {
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
      if (!options["--quiet"]) parts.push(nextStep(shown));
      emit(parts.join("\n"), output);
    } else {
      parts.push([...shown].map(([name, findings]) => renderText(name, findings)).join("\n\n"));
      if (shown.size > 1) parts.push(summary(shown));
      if (!options["--quiet"]) parts.push(nextStep(shown));
      emit(parts.join("\n\n"), output);
    }
  }
  return hasError ? 1 : 0;
}

/** @param {string[]} args */
function runFix(args) {
  const { options, positionals } = parseArgs(args);
  if (!positionals.length) throw new UsageError("고칠 마크다운 파일이 필요하다");
  const files = collectFiles(positionals);
  const config = configFrom(options, files);
  const analyzer = analyzerFor(config);
  void analyzer;
  const lines = [];
  for (const path of files) {
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
  const config = configFrom(options, []);
  const off = new Set(offRules(config));
  const width = Math.max(...names.map((name) => name.length));
  const lines = [];
  for (const [category, title] of Object.entries(CATEGORY_TITLES)) {
    const inside = names.filter((name) => ruleCategory(name) === category);
    if (!inside.length) continue;
    lines.push(`${title} (${inside.length})`);
    for (const name of inside) lines.push(`  ${name.padEnd(width)}  ${ruleSummary(name)}${off.has(name) ? " (꺼짐)" : ""}`);
    lines.push("");
  }
  let tail = `규칙 ${names.length}개`;
  if (off.size) {
    const byPreset = PRESETS[config.preset].length;
    tail += `, 그중 ${off.size}개가 꺼져 있다 (preset ${config.preset} 이 ${byPreset}개, disable 이 ${off.size - byPreset}개)`;
  }
  lines.push(`${tail}. 하나를 자세히 보려면 hanlint explain <규칙>`);
  lines.push(`프리셋은 ${PRESET_NAMES.join(", ")} 이고 hanlint init --preset <이름> 이 설정에 적는다`);
  process.stdout.write(`${lines.join("\n")}\n`);
  return 0;
}

/** 여러 줄짜리 본보기를 첫 줄에만 표를 달고 나머지는 맞춰 들여쓴다. @param {string} text @param {string} label */
function indent(text, label) {
  const pad = " ".repeat(label.length);
  return text.replace(/\n+$/, "").split("\n").map((line, index) => (index === 0 ? label : pad) + line).join("\n");
}

/** 가까운 이름을 몇 개까지 보이는가. */
const NEAR_LIMIT = 3;
/** 앞 몇 글자가 같으면 가까운 이름으로 보는가. */
const NEAR_PREFIX = 3;

/** 오타에 가까운 이름. 파이썬 cli/commands/explain.py 의 nearNames 와 같다. @param {string} query @param {string[]} names */
function nearNames(query, names) {
  const lowered = query.toLowerCase();
  /** @type {[number, string][]} */
  const scored = [];
  for (const name of names) {
    const low = name.toLowerCase();
    if (low.includes(lowered) || lowered.includes(low)) scored.push([0, name]);
    else if (low.slice(0, NEAR_PREFIX) === lowered.slice(0, NEAR_PREFIX)) scored.push([1, name]);
  }
  scored.sort((a, b) => a[0] - b[0] || (a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0));
  return scored.slice(0, NEAR_LIMIT).map(([, name]) => name);
}

/** @param {string[]} args */
function runExplain(args) {
  const { positionals } = parseArgs(args);
  const names = ruleNames();
  if (!positionals.length) {
    process.stdout.write("규칙 이름 하나가 필요하다. 예: hanlint explain doublePassive\n");
    process.stdout.write(`\n규칙 ${names.length}개를 부류로 묶어 보려면 hanlint rules, 이름만 보려면 hanlint rules --names\n`);
    return 2;
  }
  if (positionals.length !== 1) throw new UsageError("규칙 이름 하나가 필요하다. hanlint rules 로 목록을 본다");
  const wanted = positionals[0];
  if (!names.includes(wanted)) {
    const near = nearNames(wanted, names);
    const hint = near.length ? ` 이것을 찾았나: ${near.join(", ")}` : " hanlint rules 로 목록을 본다";
    throw new Error(`모르는 규칙: ${wanted}.${hint}`);
  }
  const category = ruleCategory(wanted);
  process.stdout.write(`${wanted}  (${CATEGORY_TITLES[category]})\n\n${ruleDoc(wanted)}\n`);
  const exemplar = exemplarFor(wanted);
  if (exemplar) {
    process.stdout.write("\n본보기\n");
    process.stdout.write(`${indent(exemplar.before, "  전  ")}\n`);
    process.stdout.write(`${indent(exemplar.after, "  후  ")}\n`);
    process.stdout.write(`  달라진 것: ${exemplar.moved}\n`);
  }
  const siblings = names.filter((name) => ruleCategory(name) === category && name !== wanted);
  process.stdout.write(`\n같은 부류: ${siblings.join(", ")}\n`);
  process.stdout.write(`끄려면 hanlint.toml 의 disable 에 ${wanted} 를 넣는다. 한 자리만 끄려면 <!-- hanlint-disable ${wanted} -->\n`);
  return 0;
}

/** @param {string[]} args */
function runDoctor(args) {
  const { options } = parseArgs(args);
  const config = configFrom(options, []);
  const names = ruleNames();
  const off = offRules(config);
  const lines = [
    `hanlint ${version}`,
    "",
    `node      ${process.version.replace(/^v/, "")}`,
    `설정      ${configLabel(config)}`,
    `프리셋    ${config.preset} (${PRESET_NAMES.join(", ")} 가운데)`,
    `분석기    ${config.analyzer}. kiwi 정밀 모드는 파이썬 패키지에 있다 (pip install hanlint[kiwi])`,
    `규칙      ${names.length - off.length}개 켜짐, ${off.length}개 꺼짐`,
  ];
  if (off.length) lines.push(`꺼진 규칙  ${off.join(", ")}`);
  lines.push("", "다음: hanlint 글.md 로 검사한다. 설정이 기본값이면 hanlint init 으로 파일을 만든다");
  process.stdout.write(`${lines.join("\n")}\n`);
  return 0;
}

/** 주석 달린 hanlint.toml. 파이썬 `hanlint init` 과 같은 글자다. @param {string} [preset] */
export function renderInit(preset = "blog") {
  const defaults = defaultConfig();
  const lines = [
    "# hanlint 설정. 규칙을 끄려면 disable 에 이름을 넣는다. 규칙의 기술서는 hanlint explain <규칙>.",
    "",
    "# 글의 종류. 그 종류에 안 맞는 규칙을 처음부터 끈다. disable 은 그 위에 더한다.",
  ];
  for (const [name, off] of Object.entries(PRESETS)) lines.push(`#   ${name}: ${off.length ? off.join(", ") : "전부 켠다"}`);
  lines.push(`preset = "${preset}"`, "", "# 규칙 목록과 한 줄 설명");
  for (const [category, title] of Object.entries(CATEGORY_TITLES)) {
    const inside = ruleNames().filter((name) => ruleCategory(name) === category);
    if (!inside.length) continue;
    lines.push(`#  ${title}`);
    for (const name of inside) lines.push(`#   ${name}: ${ruleSummary(name)}`);
  }
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
    "# 도입과 마지막 절이 담아야 하는 frontmatter 필드. 비어 있으면 fieldEcho 는 돌지 않는다",
    '# introFields = ["readerQuestion"]',
    '# endingFields = ["readerTakeaway"]',
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
  const preset = choose(/** @type {string} */ (options["--preset"] ?? "blog"), PRESET_NAMES, "--preset");
  if (existsSync(path) && !options["--force"]) throw new Error(`${path} 가 이미 있다. 덮어쓰려면 --force`);
  writeFileSync(path, renderInit(preset), "utf-8");
  const off = PRESETS[preset];
  const tail = off.length ? `preset ${preset} 이 ${off.length}개를 끈다` : `preset ${preset} 은 규칙을 전부 켠다`;
  process.stdout.write(`${path} 를 만들었다. ${tail}. 더 끄려면 disable 에 이름을 넣는다\n`);
  return 0;
}

/** @param {string[]} argv */
function dispatch(argv) {
  if (!argv.length) {
    process.stdout.write(`${welcome(version)}\n`);
    return 0;
  }
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
    throw new Error(`${command} 는 파이썬 패키지에 있다 (pip install hanlint). npm 은 lint, fix, print, rules, explain, doctor, init 을 제공한다`);
  }
  if (command === "lint") return runLint(rest);
  if (command === "fix") return runFix(rest);
  if (command === "print") return runPrint(rest);
  if (command === "rules") return runRules(rest);
  if (command === "explain") return runExplain(rest);
  if (command === "doctor") return runDoctor(rest);
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
