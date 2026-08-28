// @ts-check
import assert from "node:assert/strict";
import test from "node:test";

import { REGISTERS } from "../src/analysis/grammar/index.js";
import { defaultConfig } from "../src/config/settings.js";
import { exemplars } from "../src/data/exemplars.js";
import { patterns } from "../src/data/patterns.js";
import { lintText } from "../src/index.js";
import { exemplarInRegister, patternInRegister } from "../src/report/registerMatch.js";

/** 본보기 게이트가 요구하는 규칙별 설정. @param {string} name */
function configFor(name) {
  const config = defaultConfig();
  if (["keywordMissing", "keywordHeading"].includes(name)) config.keywordField = "primaryKeyword";
  if (name === "fieldEcho") config.endingFields = ["readerTakeaway"];
  return config;
}

test("every exemplar still points both ways in three registers", () => {
  for (const [name, exemplar] of exemplars()) {
    for (const register of REGISTERS) {
      const adapted = exemplarInRegister(exemplar, register);
      const config = configFor(name);
      assert.ok(lintText(adapted.before, config).some((finding) => finding.rule === name), `${name}/${register} before`);
      assert.ok(!lintText(adapted.after, config).some((finding) => finding.rule === name), `${name}/${register} after`);
    }
  }
});

test("every pattern works both ways in three registers", () => {
  const config = defaultConfig();
  for (const source of patterns()) {
    for (const register of REGISTERS) {
      const pattern = patternInRegister(source, register);
      const errors = lintText(pattern.example, config).filter((finding) => finding.severity === "error");
      assert.deepEqual(errors, [], `${pattern.name}/${register} example`);
      const caught = new Set(lintText(pattern.instead, config).map((finding) => finding.rule));
      assert.ok(pattern.avoids.every((rule) => caught.has(rule)), `${pattern.name}/${register} instead`);
    }
  }
});
