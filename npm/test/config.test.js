// @ts-check
/** 설정 읽기. TOML 부분집합 파서와 설정 검증. */
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { loadConfig } from "../src/config/loadConfig.js";
import { configFromMapping } from "../src/config/settings.js";
import { parseToml } from "../src/config/toml.js";

test("parseToml reads the hanlint subset", () => {
  const data = parseToml(`# 주석
disable = ["dash", "nounPile"]
analyzer = "surface"
headingUniformRatio = 0.8
endingRun = 6
flag = true

[dictionary]
cliches = ["우리의 여정"]
translationese = [{ pattern = "에 대한 이해", fix = "를 아는 것" }]

[tool.hanlint]
fragmentRun = 2
`);
  assert.deepEqual(data.disable, ["dash", "nounPile"]);
  assert.equal(data.analyzer, "surface");
  assert.equal(data.headingUniformRatio, 0.8);
  assert.equal(data.endingRun, 6);
  assert.equal(data.flag, true);
  assert.deepEqual(data.dictionary, { cliches: ["우리의 여정"], translationese: [{ pattern: "에 대한 이해", fix: "를 아는 것" }] });
  assert.deepEqual(data.tool, { hanlint: { fragmentRun: 2 } });
});

test("parseToml reads array tables and escapes", () => {
  const data = parseToml(`[[entry]]\npattern = "a\\\\sb"\nwhy = "따옴표 \\" 안"\n\n[[entry]]\npattern = 'raw\\s'\n`);
  const entries = /** @type {Record<string, string>[]} */ (data.entry);
  assert.equal(entries.length, 2);
  assert.equal(entries[0].pattern, "a\\sb");
  assert.equal(entries[0].why, '따옴표 " 안');
  assert.equal(entries[1].pattern, "raw\\s");
});

test("parseToml refuses what it cannot read", () => {
  assert.throws(() => parseToml('a = """여러 줄"""'), /부분집합/);
  assert.throws(() => parseToml("a = 2026-08-27"), /부분집합/);
});

test("configFromMapping validates keys", () => {
  assert.throws(() => configFromMapping({ unknown: 1 }), /모르는 설정 키/);
  assert.throws(() => configFromMapping({ analyzer: "mecab" }), /analyzer 는/);
  const config = configFromMapping({ disable: ["dash"], nounPileMin: 7 });
  assert.equal(config.disable.has("dash"), true);
  assert.equal(config.nounPileMin, 7);
});

test("loadConfig walks up to hanlint.toml or pyproject", () => {
  const root = mkdtempSync(join(tmpdir(), "hanlintConfig-"));
  writeFileSync(join(root, "hanlint.toml"), 'disable = ["dash"]\n', "utf-8");
  const nested = join(root, "a", "b");
  mkdirSync(nested, { recursive: true });
  assert.equal(loadConfig(null, nested).disable.has("dash"), true);
  const other = mkdtempSync(join(tmpdir(), "hanlintPyproject-"));
  writeFileSync(join(other, "pyproject.toml"), "[tool.hanlint]\nendingRun = 6\n", "utf-8");
  assert.equal(loadConfig(null, other).endingRun, 6);
});
