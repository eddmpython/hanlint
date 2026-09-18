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

import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { buildIndex, indexTokens, loadIndex, readDocuments } from "../src/usage/index.js";
import { FILES, decodeVarints, paragraphsOf, sentenceKey, sentencesOf } from "../src/usage/sentences.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const CORPUS = join(HERE, "..", "..", "tests", "fixtures", "usage", "corpus");
const SHARED = "회사는 리스부채를 리스개시일에 지급되지 않은 리스료의 현재가치로 측정합니다.";

test("tokens strip josa and add bigrams", () => {
  assert.deepEqual(indexTokens("회사는 리스부채를 K-IFRS 기준으로 12% 측정합니다."), [
    "회사", "리스부채", "리스", "스부", "부채", "k", "ifrs", "기준", "12", "측정합니다", "측정", "정합", "합니", "니다",
  ]);
  assert.deepEqual(indexTokens("이 는 입니다"), []);
});

test("sentence key folds spacing and numbers", () => {
  assert.equal(sentenceKey("전기  대비 12% 증가하였습니다."), sentenceKey("전기 대비 8% 증가하였습니다."));
  assert.notEqual(sentenceKey("전기 대비 증가하였습니다."), sentenceKey("전기 대비 감소하였습니다."));
});

test("paragraphs skip headings, tables, fences and bullets", () => {
  const text = "# 제목\n\n| 구분 | 값 |\n|---|---|\n\n```\n코드입니다.\n```\n\n- 항목입니다.\n(가) 가나다.\n3. 셋째입니다.\n";
  assert.deepEqual(paragraphsOf(`${text}나.붙은 항목입니다.\n`), ["항목입니다.", "가나다.", "셋째입니다.", "붙은 항목입니다."]);
  assert.deepEqual(sentencesOf("제목만 있는 줄\n마침표로 끝난다. 물음표로 끝나나? 3.5 초다.\n"), ["마침표로 끝난다.", "물음표로 끝나나?", "3.5 초다."]);
});

test("varints decode what the builder wrote", () => {
  assert.deepEqual(decodeVarints(new Uint8Array([0, 1, 127, 128, 1, 172, 2, 255, 255, 3])), [0, 1, 127, 128, 300, 65535]);
});

test("build is deterministic, folds shared sentences, and search ranks", () => {
  const root = mkdtempSync(join(tmpdir(), "hanlintUsage-"));
  const first = buildIndex("report", readDocuments(CORPUS), join(root, "one"));
  const second = buildIndex("report", readDocuments(CORPUS), join(root, "two"));
  assert.deepEqual(first, second);
  assert.deepEqual(first, { documents: 3, sentences: 11, terms: 135 });
  for (const name of FILES) {
    assert.ok(readFileSync(join(root, "one", "report", name)).equals(readFileSync(join(root, "two", "report", name))), name);
  }
  const lines = readFileSync(join(root, "one", "report", "sentences.tsv"), "utf-8").split("\n");
  assert.equal(lines[0], `3\ta001\t${SHARED}`);
  assert.ok(!lines.some((line) => line.includes("리스부채의 최초 측정금액")), "제목은 문장이 아니다");
  const index = loadIndex("report", join(root, "one"));
  assert.ok(index);
  const hits = index.search("리스부채 측정", 2);
  assert.deepEqual(hits.map((hit) => hit.text), [SHARED, "리스부채는 이자비용을 반영하여 증가하고 지급한 리스료를 반영하여 감소합니다."]);
  assert.equal(hits[0].documents, 3);
  assert.equal(hits[0].source, "a001");
  assert.ok(hits[0].score > hits[1].score && hits[1].score > 0);
  assert.deepEqual(index.search("없는낱말", 5), []);
  assert.deepEqual(index.search("리스부채 측정", 5), index.search("측정 리스부채", 5));
  assert.equal(loadIndex("report", join(root, "none")), null);
  writeFileSync(join(root, "one", "report", "meta.json"), '{"format": 99}');
  assert.throws(() => loadIndex("report", join(root, "one")), /format/);
});
