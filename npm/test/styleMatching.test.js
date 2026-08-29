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
      const afterFindings = lintText(adapted.after, config);
      assert.ok(!afterFindings.some((finding) => finding.rule === name), `${name}/${register} after`);
      // 규칙 A 의 답이 규칙 B 의 문제가 되면 충돌이다. after 는 어느 규칙의 error 에도 안 잡혀야 한다. 파이썬 게이트와 같다.
      const conflicts = [...new Set(afterFindings.filter((finding) => finding.severity === "error").map((finding) => finding.rule))].sort();
      assert.deepEqual(conflicts, [], `${name}/${register} after conflicts`);
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
