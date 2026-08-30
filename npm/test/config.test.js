// @ts-check
/** 설정 읽기. TOML 부분집합 파서와 설정 검증. */
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { loadConfig } from "../src/config/loadConfig.js";
import { configFromMapping } from "../src/config/settings.js";
import { exemplarFor } from "../src/data/exemplars.js";
import { patchFor } from "../src/data/patches.js";
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
  assert.throws(() => configFromMapping({ analyzer: "kiwi" }), /빠졌다/);
  assert.throws(() => configFromMapping({ ignoreFences: "course-scene" }), /문자열 배열/);
  assert.throws(() => configFromMapping({ endingFields: "readerTakeaway" }), /문자열 배열/);
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

test("project exemplars override built-ins and reject overlap", () => {
  const entry = {
    rule: "translationese",
    before: "우리 조직의 전 문장입니다.",
    after: "우리 조직의 후 문장입니다.",
    moved: "조직의 동사로 바꿈",
    presets: ["docs"],
  };
  const config = configFromMapping({ exemplars: [entry] });
  assert.equal(exemplarFor("translationese", "docs", config.exemplars)?.before, entry.before);
  assert.notEqual(exemplarFor("translationese", "blog", config.exemplars)?.before, entry.before);
  const defaultNounPile = configFromMapping({ exemplars: [{ ...entry, rule: "nounPile", presets: [] }] });
  assert.equal(exemplarFor("nounPile", "blog", defaultNounPile.exemplars)?.before, entry.before);
  assert.ok(exemplarFor("nounPile", "docs", defaultNounPile.exemplars)?.before.startsWith("사용자 인증"));
  assert.throws(() => configFromMapping({ exemplars: [entry, entry] }), /프리셋이 겹친다/);
  assert.throws(() => configFromMapping({ exemplars: [{ ...entry, rule: "noSuchRule" }] }), /모르는 규칙/);
});

test("loadConfig reads project exemplar array tables", () => {
  const root = mkdtempSync(join(tmpdir(), "hanlintExemplars-"));
  writeFileSync(
    join(root, "hanlint.toml"),
    '[[exemplars]]\nrule = "translationese"\nbefore = "전입니다."\nafter = "후입니다."\n' +
      'moved = "서술어로 바꿈"\npresets = ["blog"]\n',
    "utf-8",
  );
  assert.equal(loadConfig(null, root).exemplars[0].rule, "translationese");
});

test("project patches require one exact selector", () => {
  const entry = {
    rule: "translationese",
    before: "설계에 대한 이해가 필요합니다.",
    after: "설계를 알아야 합니다.",
    moved: "명사구를 서술어로 풂",
    cue: "에  대한",
    reader: "new",
    presets: ["blog"],
  };
  const config = configFromMapping({ patches: [entry] });
  const chosen = patchFor("translationese", "blog", entry.before, entry.before, "에 대한", "new", config.patches);
  assert.equal(chosen?.cue, "에 대한");
  const folded = entry.before.normalize("NFD").replaceAll(" ", "\n  ");
  assert.equal(patchFor("translationese", "blog", folded, folded, "에 대한", "new", config.patches), chosen);
  assert.equal(patchFor("translationese", "docs", entry.before, entry.before, "에 대한", "new", config.patches), undefined);
  assert.equal(patchFor("translationese", "blog", "다른 문장입니다.", "다른 문장입니다.", "에 대한", "new", config.patches), undefined);
  assert.equal(patchFor("translationese", "blog", entry.before, entry.before, "에 대해", "new", config.patches), undefined);
  assert.equal(patchFor("translationese", "blog", entry.before, entry.before, "에 대한", "known", config.patches), undefined);
  assert.equal(patchFor("translationese", "blog", entry.before, entry.before, "에 대한", "new", [chosen, chosen]), undefined);
  const other = { ...entry, before: "자료에 대한 이해가 필요합니다.", after: "자료를 알아야 합니다." };
  const two = configFromMapping({ patches: [entry, other] }).patches;
  assert.equal(patchFor("translationese", "blog", other.before, other.before, "에 대한", "new", two), two[1]);
  const marked = {
    ...entry,
    before: "`설계`에 대한 이해가 필요합니다.",
    after: "`설계`를 알아야 합니다.",
    sentence: entry.before,
  };
  const markedPatch = configFromMapping({ patches: [marked] }).patches[0];
  assert.equal(patchFor("translationese", "blog", marked.before, entry.before, "에 대한", "new", [markedPatch]), markedPatch);
  assert.equal(patchFor("translationese", "blog", entry.before, entry.before, "에 대한", "new", [markedPatch]), undefined);
  assert.ok(markedPatch.before.startsWith("`설계`"));
  assert.throws(() => configFromMapping({ patches: [entry, entry] }), /선택 조건이 겹친다/);
  assert.throws(() => configFromMapping({ patches: [{ ...entry, presets: [] }] }), /비지 않은 문자열 배열/);
  assert.throws(() => configFromMapping({ patches: [{ ...entry, reader: "any" }] }), /reader/);
  assert.throws(() => configFromMapping({ patches: [{ ...entry, sentence: "" }] }), /sentence/);
  assert.throws(() => configFromMapping({ patches: [{ ...entry, sourceText: "" }] }), /sourceText/);
});

test("loadConfig reads project patch array tables", () => {
  const root = mkdtempSync(join(tmpdir(), "hanlintPatches-"));
  writeFileSync(
    join(root, "hanlint.toml"),
    '[[patches]]\nrule = "translationese"\nbefore = "전입니다."\nafter = "후입니다."\n' +
      'moved = "서술어로 바꿈"\ncue = "에 대한"\nreader = "new"\npresets = ["blog"]\n',
    "utf-8",
  );
  assert.equal(loadConfig(null, root).patches[0].cue, "에 대한");
});
