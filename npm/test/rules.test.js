// @ts-check
/** 규칙 fixture. 파이썬과 같은 tests/fixtures/rules/*.json 을 읽어 catch 는 잡히고 spare 는 안 잡혀야 한다. */
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { configFromMapping, lintText, ruleNames } from "../src/index.js";
import { loadRuleDocs, loadRuleMechanisms } from "../src/data/load.js";
import { MECHANISMS, RULES, docSection } from "../src/rules/registry.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "..", "..", "tests", "fixtures", "rules");
const RULE_DIRS = ["sentence", "paragraph", "structure", "document", "orthography", "code", "screen"].map((d) => join(HERE, "..", "src", "rules", d));
const EM_DASH = String.fromCharCode(0x2014);
const EN_DASH = String.fromCharCode(0x2013);

test("technical names require context while explicit project vocabulary stays enforceable", () => {
  for (const text of ["쿼리 실행", "원자적 교체", "릴리스 관리", "스키마 확인", "뷰포트 설정"]) {
    const findings = lintText(text, configFromMapping({ preset: "screen" })).filter(f => f.rule === "screenWord");
    assert.ok(findings.length);
    assert.ok(findings.every(f => f.severity === "notice" && f.fix === null && f.replacement === null));
  }
  const config = configFromMapping({ preset: "screen", dictionary: { screenWord: [{ pattern: "회사{조사}", fix: "수임처" }] } });
  const findings = lintText("회사 선택", config).filter(f => f.rule === "screenWord");
  assert.equal(findings[0].severity, "error");
  assert.equal(findings[0].fix, "수임처 선택");
});

test("calqueFrame builtin pairs are notices and project pairs are errors", () => {
  const text = "캐스팅 장갑은 아직 원투 글에 잇지 못했습니다. 할 일 판의 이 일은 아직 닫지 않았습니다.";
  const builtin = lintText(text).filter(f => f.rule === "calqueFrame");
  assert.deepEqual(builtin.map(f => [f.severity, f.fix]), [["notice", null]]);
  const config = configFromMapping({ dictionary: { calqueFrame: [{ pattern: "할 일 판", fix: "투두리스트", why: "는 이 프로젝트에서 투두리스트다" }] } });
  const project = lintText(text, config).filter(f => f.rule === "calqueFrame");
  assert.deepEqual(project.map(f => f.severity), ["notice", "error"]);
  assert.equal(project[1].fix, "투두리스트의 이 일은 아직 닫지 않았습니다.");
});

test("unless skips an entry only in the sentence it matches", () => {
  const config = configFromMapping({ disable: ["spacing"], dictionary: { cliches: [{ pattern: "맡겼", unless: "(?:에게|한테)(?![가-힣])" }] } });
  const lines = lintText("발행을 맡겼습니다.\n\n블로그팀에게 발행을 맡겼습니다.\n", config).filter(f => f.rule === "cliche").map(f => f.line);
  assert.deepEqual(lines, [1]);
});

test("keep drops only the overlapping span and candidates reach the finding", () => {
  const config = configFromMapping({ disable: ["spacing"], dictionary: { cliches: [{ pattern: "자리", keep: "그 자리에서|자리가 나", candidates: ["위치"] }] } });
  const found = lintText("그 자리에서 커서 자리를 고칩니다. 대기열에 자리가 나면 넣습니다.\n", config).filter(f => f.rule === "cliche");
  assert.deepEqual(found.map(f => [f.quote, f.candidates.map(c => c.text)]), [["그 자리에서 커서 자리를 고칩니다.", ["위치"]]]);
});

test("dictionary rules read list items, table cells, headings and image text", () => {
  const config = configFromMapping({ disable: ["spacing"], dictionary: { cliches: [{ pattern: "자리" }] } });
  const text = "## 위험한 자리\n\n- 서는 자리 보기\n1. 둘째 **자리**\n\n| 칸 | 값 |\n|---|---|\n| 심볼 자리 | `코드 자리` |\n\n![구조함 자리](a.png)\n\n> 인용 자리\n";
  const found = lintText(text, config).filter(f => f.rule === "cliche").map(f => [f.line, f.at, f.quote]);
  assert.deepEqual(found, [[1, -1, "위험한 자리"], [3, -1, "서는 자리 보기"], [4, -1, "둘째 자리"], [8, -1, "심볼 자리"], [10, -1, "구조함 자리"]]);
});

test("protectedTerms drop a finding whose span overlaps the term", () => {
  const spacingOf = (/** @type {Record<string, unknown>} */ mapping) =>
    lintText("할수있어 앱은 볼수 없습니다.", configFromMapping(mapping)).filter(f => f.rule === "spacing").map(f => f.fragment);
  assert.deepEqual(spacingOf({}), ["할수있", "볼수 없"]);
  assert.deepEqual(spacingOf({ protectedTerms: ["할수있어"] }), ["볼수 없"]);
  assert.deepEqual(spacingOf({ protectedTerms: ["있어 앱"] }), ["볼수 없"]);
  const project = { dictionary: { spacing: [{ pattern: "물때", fix: "물 때" }] } };
  assert.equal(lintText("물때는 사리 전후가 좋습니다.", configFromMapping(project)).filter(f => f.rule === "spacing").length, 1);
  assert.equal(lintText("물때는 사리 전후가 좋습니다.", configFromMapping({ ...project, protectedTerms: ["물때"] })).filter(f => f.rule === "spacing").length, 0);
});

/** fixture 의 자리표시자. @param {string} text */
function expandTokens(text) {
  return text.replaceAll("{em}", EM_DASH).replaceAll("{en}", EN_DASH).replaceAll("{dot}", ".");
}

const fixtureFiles = readdirSync(FIXTURES)
  .filter((f) => f.endsWith(".json"))
  .sort();

for (const file of fixtureFiles) {
  test(`fixture ${file}`, () => {
    const data = JSON.parse(readFileSync(join(FIXTURES, file), "utf-8"));
    assert.equal(data.rule, file.replace(/\.json$/, ""));
    const config = configFromMapping(data.config ?? {});
    for (const text of data.catch) {
      const rules = lintText(expandTokens(text), config).map((f) => f.rule);
      assert.ok(rules.includes(data.rule), `잡아야 하는데 안 잡았다: ${JSON.stringify(text)} → ${rules}`);
    }
    for (const text of data.spare) {
      const rules = lintText(expandTokens(text), config).map((f) => f.rule);
      assert.ok(!rules.includes(data.rule), `잡지 말아야 하는데 잡았다: ${JSON.stringify(text)}`);
    }
  });
}

test("every rule has a fixture, a doc, and a file", () => {
  const names = ruleNames();
  const fixtures = fixtureFiles.map((f) => f.replace(/\.json$/, ""));
  assert.deepEqual(names, fixtures);
  assert.deepEqual(names, Object.keys(loadRuleDocs()).sort());
  const files = RULE_DIRS.flatMap((dir) => readdirSync(dir).filter((f) => f.endsWith(".js")).map((f) => f.replace(/\.js$/, ""))).sort();
  assert.deepEqual(names, files);
  for (const rule of RULES) assert.equal(typeof rule.run, "function", rule.name);
});

test("every rule names one of the closed mechanisms and matches the python projection", () => {
  assert.deepEqual(Object.keys(MECHANISMS), ["dictionary", "repeat", "threshold", "contrast", "reader"]);
  const mine = Object.fromEntries(RULES.map((rule) => [rule.name, rule.mechanism]).sort());
  assert.deepEqual(mine, loadRuleMechanisms());
  for (const mechanism of Object.values(mine)) assert.ok(mechanism in MECHANISMS, mechanism);
});

test("docSection stops at the next section label and joins continuation lines", () => {
  const doc = "첫 줄.\n\n왜: 이유.\n어디서: 출처.\n고치기: 하나.\n    둘.\n안 잡는 것: 셋.";
  assert.equal(docSection(doc, "고치기:"), "하나. 둘.");
  assert.equal(docSection(doc, "안 잡는 것:"), "셋.");
  assert.equal(docSection(doc, "왜:"), "이유.");
});
