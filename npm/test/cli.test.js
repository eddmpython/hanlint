// @ts-check
/** 명령줄 계약. 종료 코드 0 (지적 없음), 1 (error 지적), 2 (파일이나 설정 문제). */
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
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
  assert.ok(result.out.includes(`${bad}:3  [cliche]`));
  const ok = run([clean]);
  assert.equal(ok.code, 0);
  assert.ok(ok.out.includes("집은 자리 없음"));
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

test("init writes config and refuses to overwrite", () => {
  const target = join(dir, "hanlint.toml");
  assert.equal(run(["init", "--path", target]).code, 0);
  const text = readFileSync(target, "utf-8");
  assert.ok(text.includes("disable = []") && text.includes("#   doublePassive:"));
  const again = run(["init", "--path", target]);
  assert.equal(again.code, 2);
  assert.ok(again.err.includes("이미 있다"));
  assert.equal(run(["init", "--path", target, "--force"]).code, 0);
});
