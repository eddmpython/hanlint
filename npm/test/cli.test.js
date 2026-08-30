// @ts-check
/** 명령줄 계약. 종료 코드 0 (지적 없음), 1 (error 지적), 2 (파일이나 설정 문제). */
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const BIN = join(dirname(fileURLToPath(import.meta.url)), "..", "bin", "hanlint.js");
const BAD = "## 절\n\n핵심은 속도입니다.\n";
const CLEAN = "## 절\n\n파일을 엽니다. 그러면 표가 생길까요? 작업 폴더에 생깁니다.\n";

/** @param {string[]} args */
function run(args) {
  const result = spawnSync(process.execPath, [BIN, ...args], { encoding: "utf-8" });
  return { code: result.status, out: result.stdout, err: result.stderr };
}

const dir = mkdtempSync(join(tmpdir(), "hanlintCli-"));
const bad = join(dir, "bad.md");
const clean = join(dir, "clean.md");
writeFileSync(bad, BAD, "utf-8");
writeFileSync(clean, CLEAN, "utf-8");

test("lint exit codes and text", () => {
  const result = run([bad, "--no-color"]);
  assert.equal(result.code, 1);
  assert.ok(result.out.startsWith("설정: 기본값\n"));
  assert.ok(result.out.includes(`${bad}:3  [cliche]`));
  const ok = run([clean, "--quiet"]);
  assert.equal(ok.code, 0);
  assert.ok(ok.out.includes("집은 자리 없음") && !ok.out.includes("설정:"));
});

test("severity, compact, stdin, summary", () => {
  const mixed = join(dir, "mixed.md");
  writeFileSync(mixed, "## 절\n\n핵심은 속도입니다. 파일을 엽니다. 표가 보입니다. 열이 다섯입니다. 값을 고칩니다.\n", "utf-8");
  // 요약은 거른 뒤가 아니라 글에 있는 것을 센다. 보여 줄 것을 고르는 옵션이 수를 바꾸면 거짓말이다
  const compact = run([mixed, "--format", "compact", "--errors-only", "--quiet"]);
  assert.equal(compact.code, 1);
  const compactLines = compact.out.trimEnd().split("\n");
  assert.equal(compactLines[0], `${mixed}:3 [cliche] \`핵심은\` 결론을 포장하는 말이다. 핵심이 무엇인지 그 자리에서 직접 쓴다 (글쓰기 스킬)`);
  assert.match(compactLines[compactLines.length - 1], /^파일 1개, error 1, notice [1-9]/);
  const notices = run([mixed, "--severity", "notice", "--format", "json"]);
  const findings = JSON.parse(notices.out).files[0].findings;
  assert.ok(findings.length && findings.every((f) => f.severity === "notice"));
  const piped = spawnSync(process.execPath, [BIN, "-", "--path", "초안.md", "--format", "compact", "--quiet"], { encoding: "utf-8", input: BAD });
  assert.equal(piped.status, 1);
  assert.ok(piped.stdout.startsWith("초안.md:3 [cliche]"));
  const many = run([bad, clean, "--quiet"]);
  assert.ok(many.out.trimEnd().endsWith("파일 2개, error 1, notice 0"));
});

test("fix applies fragments and dry run keeps the file", () => {
  const draft = join(dir, "draft.md");
  writeFileSync(draft, "## 절\n\n모든 분야에 있어서 기준이 필요합니다.\r\n둘째 줄입니다.\r\n", "utf-8");
  const before = readFileSync(draft, "utf-8");
  const preview = run(["fix", draft, "--dry-run"]);
  assert.equal(preview.code, 0);
  assert.ok(preview.out.includes("에 있어서 → 에서") && preview.out.includes("미리보기"));
  assert.equal(readFileSync(draft, "utf-8"), before);
  assert.ok(run(["fix", draft]).out.includes("1곳 고침, 0곳 건너뜀"));
  const after = readFileSync(draft, "utf-8");
  assert.ok(after.includes("모든 분야에서 기준이") && after.includes("\r\n"));
  assert.equal(run([draft, "--errors-only", "--format", "compact", "--quiet"]).code, 0);
});

test("print gives layers", () => {
  const all = JSON.parse(run(["print", bad]).out);
  assert.equal(all.layer, "all");
  assert.equal(all.sentences[0].text, "핵심은 속도입니다.");
  assert.deepEqual(all.paragraphs[0].sentences, [0]);
  const only = JSON.parse(run(["print", bad, "--layer", "sections"]).out);
  assert.deepEqual(Object.keys(only), ["version", "layer", "sections"]);
});

test("lint json and github", () => {
  const json = run([bad, "--format", "json"]);
  assert.equal(json.code, 1);
  assert.equal(JSON.parse(json.out).files[0].findings[0].rule, "cliche");
  const github = run(["lint", bad, "--format", "github"]);
  assert.ok(github.out.startsWith("::error file="));
});

test("disable and output file", () => {
  assert.equal(run([bad, "--disable", "cliche"]).code, 0);
  const target = join(dir, "out.txt");
  assert.equal(run([bad, "--output", target]).code, 1);
  assert.ok(readFileSync(target, "utf-8").includes("[cliche]"));
});

test("missing file, python-only commands, unknown option are 2", () => {
  const missing = run([join(dir, "없는파일.md")]);
  assert.equal(missing.code, 2);
  assert.ok(missing.err.includes("찾지 못했다"));
  const audit = run(["audit", bad]);
  assert.equal(audit.code, 2);
  assert.ok(audit.err.includes("파이썬 패키지"));
  const packet = run(["packet", bad]);
  assert.equal(packet.code, 2);
  assert.ok(packet.err.includes("파이썬 패키지"));
  assert.equal(run([bad, "--severity", "bogus"]).code, 2);
  assert.equal(run([bad, "--bogus"]).code, 2);
});

test("rules, explain, version", () => {
  const rules = run(["rules"]);
  assert.equal(rules.code, 0);
  assert.ok(rules.out.includes("doublePassive") && rules.out.includes("규칙 "));
  const doc = run(["explain", "doublePassive"]);
  assert.ok(doc.out.includes("왜:") && doc.out.includes("고치기:"));
  const unknown = run(["explain", "noSuchRule"]);
  assert.equal(unknown.code, 2);
  assert.ok(unknown.err.includes("모르는 규칙"));
  assert.ok(execFileSync(process.execPath, [BIN, "--version"], { encoding: "utf-8" }).startsWith("hanlint "));
});

test("project exemplar reaches lint, rules, and explain", () => {
  const room = mkdtempSync(join(tmpdir(), "hanlintExemplarCli-"));
  const config = join(room, "hanlint.toml");
  const draft = join(room, "bad.md");
  writeFileSync(
    config,
    '[[exemplars]]\nrule = "cliche"\nbefore = "조직 전입니다."\nafter = "조직 후입니다."\n' +
      'moved = "결론을 직접 씀"\npresets = ["blog"]\n',
    "utf-8",
  );
  writeFileSync(draft, BAD, "utf-8");
  const lint = JSON.parse(run([draft, "--config", config, "--format", "json"]).out);
  assert.equal(lint.files[0].findings.find((finding) => finding.rule === "cliche").exemplar.before, "조직 전입니다.");
  const rules = JSON.parse(run(["rules", "--config", config, "--format", "json"]).out);
  assert.equal(rules.rules.find((rule) => rule.name === "cliche").exemplar.before, "조직 전입니다.");
  const explain = JSON.parse(run(["explain", "cliche", "--config", config, "--format", "json"]).out);
  assert.equal(explain.exemplar.before, "조직 전입니다.");
});

test("init writes config and refuses to overwrite", () => {
  const target = join(dir, "hanlint.toml");
  assert.equal(run(["init", "--output", target]).code, 0);
  const text = readFileSync(target, "utf-8");
  assert.ok(text.includes("disable = []") && text.includes("#   doublePassive:") && text.includes("# [[exemplars]]"));
  const again = run(["init", "--output", target]);
  assert.equal(again.code, 2);
  assert.ok(again.err.includes("이미 있다"));
  assert.equal(run(["init", "--output", target, "--force"]).code, 0);
});

test("welcome screen when no arguments", () => {
  const room = mkdtempSync(join(tmpdir(), "hanlintWelcome-"));
  writeFileSync(join(room, "초안.md"), CLEAN, "utf-8");
  const result = spawnSync(process.execPath, [BIN], { encoding: "utf-8", cwd: room });
  assert.equal(result.status, 0);
  assert.ok(result.stdout.includes("hanlint 초안.md"));
  assert.ok(result.stdout.includes("이 폴더의 마크다운: 초안.md"));
  assert.ok(result.stdout.includes("hanlint doctor"));

  const empty = mkdtempSync(join(tmpdir(), "hanlintEmpty-"));
  const bare = spawnSync(process.execPath, [BIN], { encoding: "utf-8", cwd: empty });
  assert.equal(bare.status, 0);
  assert.ok(bare.stdout.includes("이 폴더에는 검사할 마크다운이 없다"));
});

test("folder argument finds markdown below", () => {
  const room = mkdtempSync(join(tmpdir(), "hanlintFolder-"));
  mkdirSync(join(room, "안"), { recursive: true });
  writeFileSync(join(room, "하나.md"), BAD, "utf-8");
  writeFileSync(join(room, "안", "둘.md"), CLEAN, "utf-8");
  writeFileSync(join(room, "그림.png"), "bytes", "utf-8");
  const result = run([room, "--format", "compact", "--quiet"]);
  assert.equal(result.code, 1);
  assert.ok(result.out.includes("하나.md") && !result.out.includes("그림.png"));
  assert.ok(result.out.includes("파일 2개"));

  const empty = mkdtempSync(join(tmpdir(), "hanlintNoMd-"));
  const nothing = run([empty]);
  assert.equal(nothing.code, 2);
  assert.ok(nothing.err.includes("안에 마크다운 파일이 없다"));
});

test("next step line tells what to do", () => {
  assert.ok(run([clean]).out.includes("다음: 세어서 잡히는 결함이 없다"));
  assert.ok(run([bad, "--errors-only"]).out.includes("다음: error"));
  assert.ok(!run([bad, "--errors-only", "--quiet"]).out.includes("다음:"));
});

test("doctor and presets", () => {
  const room = mkdtempSync(join(tmpdir(), "hanlintDoctor-"));
  const config = join(room, "hanlint.toml");
  const made = run(["init", "--output", config, "--preset", "docs"]);
  assert.equal(made.code, 0);
  assert.ok(made.out.includes("preset docs 이"));
  assert.ok(readFileSync(config, "utf-8").includes('preset = "docs"'));

  const doctor = run(["doctor", "--config", config]);
  assert.equal(doctor.code, 0);
  assert.ok(doctor.out.includes("프리셋    docs") && doctor.out.includes("개 켜짐"));

  const reference = join(room, "참고.md");
  writeFileSync(reference, "## 절\n\n파일을 엽니다. 값을 넣습니다.\n", "utf-8");
  const linted = run([reference, "--config", config, "--format", "compact", "--quiet"]);
  assert.equal(linted.code, 0);
  assert.ok(!linted.out.includes("noQuestion"));
});

test("explain suggests near names and lists siblings", () => {
  const typo = run(["explain", "doublePasive"]);
  assert.equal(typo.code, 2);
  assert.ok(typo.err.includes("이것을 찾았나: doubleNegative, doublePassive"));
  const bare = run(["explain"]);
  assert.equal(bare.code, 2);
  assert.ok(bare.out.includes("부류로 묶어 보려면 hanlint rules"));
  const found = run(["explain", "moreLater"]);
  assert.equal(found.code, 0);
  assert.ok(found.out.includes("글의 짜임에서 세는 것") && found.out.includes("같은 부류:"));
});

test("rules groups by category and marks off", () => {
  const room = mkdtempSync(join(tmpdir(), "hanlintRules-"));
  const config = join(room, "hanlint.toml");
  writeFileSync(config, 'preset = "report"\n', "utf-8");
  const grouped = run(["rules", "--config", config]);
  assert.equal(grouped.code, 0);
  assert.ok(grouped.out.includes("문장 안에서 세는 것 (") && grouped.out.includes("표기와 띄어쓰기 ("));
  assert.ok(grouped.out.includes("(꺼짐)") && grouped.out.includes("preset report 이"));
  const names = run(["rules", "--names"]).out.trim().split("\n");
  assert.deepEqual(names, [...names].sort());
  assert.ok(names.includes("moreLater"));
});
