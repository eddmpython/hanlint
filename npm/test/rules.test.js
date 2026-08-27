// @ts-check
/** 규칙 fixture. 파이썬과 같은 tests/fixtures/rules/*.json 을 읽어 catch 는 잡히고 spare 는 안 잡혀야 한다. */
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { configFromMapping, lintText, ruleNames } from "../src/index.js";
import { loadRuleDocs } from "../src/data/load.js";
import { RULES } from "../src/rules/registry.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "..", "..", "tests", "fixtures", "rules");
const RULE_DIRS = ["sentence", "paragraph", "structure", "document", "orthography", "code"].map((d) => join(HERE, "..", "src", "rules", d));
const EM_DASH = String.fromCharCode(0x2014);
const EN_DASH = String.fromCharCode(0x2013);

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
