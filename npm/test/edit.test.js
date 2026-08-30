// @ts-check
/** 고치기. 조각을 원문에서 찾아 바꾸고 못 찾거나 여럿이면 건너뛴다. 파이썬 tests/edit 과 같은 사례다. */
import assert from "node:assert/strict";
import test from "node:test";

import { applyFixes, lintText } from "../src/index.js";

const DOT = ".";
const TEXT = `## 절\n\n모든 분야에 있어서 기준이 필요합니다. 파일을 확인하세요${DOT} 노력하지 않으면 안 됩니다. 결과가 저장되어집니다.\n\n\`에 있어서\` 는 번역투라고 **설명**합니다.\n`;

/** @param {string} text */
function rulesOf(text) {
  return new Set(lintText(text).map((f) => f.rule));
}

test("applies every machine fix and the findings vanish", () => {
  const result = applyFixes(TEXT, lintText(TEXT));
  assert.deepEqual(result.applied, [
    [3, "에 있어서", "에서"],
    [3, `세요${DOT}`, "세요"],
    [3, "하지 않으면 안 됩니다", "해야 합니다"],
    [3, "되어집", "됩"],
  ]);
  assert.deepEqual(result.skipped, []);
  assert.ok(result.text.includes("모든 분야에서 기준이 필요합니다. 파일을 확인하세요 노력해야 합니다. 결과가 저장됩니다."));
  assert.ok(result.text.includes("`에 있어서` 는"));
  const after = rulesOf(result.text);
  for (const rule of ["translationese", "imperativePeriod", "doubleNegative", "doublePassive"]) assert.ok(!after.has(rule), rule);
});

test("does not change a quoted double passive", () => {
  const text = '## 절\n\n문서에는 "결과가 저장되어집니다."라고 적혀 있습니다.\n';
  const finding = lintText(text).find((item) => item.rule === "doublePassive");
  assert.ok(finding && finding.replacement === null && finding.candidates.length);
  const result = applyFixes(text, [finding]);
  assert.equal(result.text, text);
  assert.deepEqual(result.applied, []);
});

test("skips ambiguous and unfindable fragments", () => {
  const ambiguous = "## 절\n\n모든 분야에 있어서 기준과 방식에 있어서 차이가 있습니다.\n";
  const result = applyFixes(ambiguous, lintText(ambiguous));
  assert.equal(result.text, ambiguous);
  assert.equal(result.skipped.length, 2);
  const hidden = "## 절\n\n모든 분야에 **있어서** 기준이 필요합니다.\n";
  const skipped = applyFixes(hidden, lintText(hidden));
  assert.equal(skipped.text, hidden);
  assert.ok(skipped.skipped[0][2].includes("못 찾았다"));
});

test("quoted mentions are not findings", () => {
  const rules = rulesOf("## 절\n\nAI 가 자주 쓰는 표현은 `핵심은`, \"결국 중요한 것은\" 처럼 지웁니다.\n");
  assert.ok(!rules.has("cliche"));
  assert.ok(rulesOf("## 절\n\n핵심은 속도입니다.\n").has("cliche"));
});
