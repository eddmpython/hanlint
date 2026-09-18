// @ts-check
/** 용례 빈도표. 종류 고르기, 조회, nounPile 이 관용 연쇄를 접는 것. 파이썬 tests/usage/testCounts.py 와 같은 사례다. */
import assert from "node:assert/strict";
import test from "node:test";

import { nounRuns } from "../src/analysis/index.js";
import { USAGE_KINDS, USAGE_OF, configFromMapping } from "../src/config/settings.js";
import { lintText } from "../src/index.js";
import { attested, chainDocuments, usageKindOf, usageTable } from "../src/usage/index.js";

const ATTESTED = "정관상 배당절차 개선방안 이행 가부";
const PILE = "가상환경 생성 후 패키지 설치 확인";

/** @param {string} text @param {Record<string, unknown>} mapping */
function nounPiles(text, mapping) {
  return lintText(text, configFromMapping(mapping)).filter((f) => f.rule === "nounPile").map((f) => f.quote);
}

test("preset decides the kind and config overrides", () => {
  assert.equal(usageKindOf(configFromMapping({ preset: "report" })), "report");
  assert.equal(usageKindOf(configFromMapping({ preset: "blog" })), null);
  assert.equal(usageKindOf(configFromMapping({ preset: "blog", usageKind: "report" })), "report");
  assert.equal(usageKindOf(configFromMapping({ preset: "report", usageKind: "" })), null);
  assert.throws(() => configFromMapping({ usageKind: "novel" }), /usageKind/);
});

test("every declared kind has a table", () => {
  for (const kind of Object.values(USAGE_OF)) assert.ok(USAGE_KINDS.includes(kind));
  for (const kind of USAGE_KINDS) {
    const table = usageTable(kind);
    assert.equal(table.kind, kind);
    assert.ok(table.documents > 0 && Object.keys(table.chains).length > 0);
  }
});

test("chain keys match nounRuns", () => {
  const [chain] = nounRuns(`${ATTESTED} 항목을 적었습니다.`)[0];
  assert.equal(chain.join(" "), ATTESTED);
  assert.ok(chainDocuments(chain, "report") >= 3);
  assert.ok(attested(chain, "report", 3));
  assert.ok(!attested(nounRuns(PILE)[0][0], "report", 2));
});

test("report folds attested chains only", () => {
  const text = `${ATTESTED} 항목을 적었습니다.\n\n${PILE} 절차를 따릅니다.\n`;
  assert.deepEqual(nounPiles(text, { preset: "report" }), [`${PILE} 절차를 따릅니다.`]);
  assert.equal(nounPiles(text, { preset: "blog" }).length, 2);
  assert.equal(nounPiles(text, { preset: "report", usageKind: "" }).length, 2);
  assert.equal(nounPiles(text, { preset: "report", usageMin: 10_000 }).length, 2);
});

test("longer run around an attested chain is still a pile", () => {
  const text = `${ATTESTED} 검토 결과를 적었습니다.\n`;
  assert.deepEqual(nounPiles(text, { preset: "report" }), [`${ATTESTED} 검토 결과를 적었습니다.`]);
});
