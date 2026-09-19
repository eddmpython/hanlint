// @ts-check
/** 용례 빈도표. 종류 고르기, 조회, nounPile 이 관용 연쇄를 접는 것. 파이썬 tests/usage/testCounts.py 와 같은 사례다. */
import assert from "node:assert/strict";
import test from "node:test";

import { nounRuns } from "../src/analysis/index.js";
import { USAGE_KINDS, USAGE_OF, configFromMapping } from "../src/config/settings.js";
import { lintText } from "../src/index.js";
import { attested, chainDocuments, conventional, patternDocuments, usageKindOf, usageTable } from "../src/usage/index.js";

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

import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { buildIndex, indexTokens, listIndexes, loadIndex, queryCores, readDocuments } from "../src/usage/index.js";
import { FILES, decodeVarints, neighbourOf, paragraphsOf, predicateStem, sentenceKey, sentencesOf } from "../src/usage/sentences.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const CORPUS = join(HERE, "..", "..", "tests", "fixtures", "usage", "corpus");
const SHARED = "회사는 창고 임차료를 계약 첫날에 한꺼번에 내지 않고 달마다 나누어 냅니다.";

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
  assert.deepEqual(sentencesOf("제목만 있는 줄\n평가 보고6.\n마침표로 끝난다. 물음표로 끝나나? 3.5 초다.\n"), ["마침표로 끝난다.", "물음표로 끝나나?", "3.5 초다."]);
});

test("shard size does not change the bytes", () => {
  const root = mkdtempSync(join(tmpdir(), "hanlintUsageShard-"));
  const whole = buildIndex("report", readDocuments(CORPUS), join(root, "whole"));
  const sharded = buildIndex("report", readDocuments(CORPUS), join(root, "sharded"), 4);
  assert.deepEqual(whole, sharded);
  for (const name of FILES) {
    assert.ok(readFileSync(join(root, "whole", "report", name)).equals(readFileSync(join(root, "sharded", "report", name))), name);
  }
});

test("jsonl lines are documents", () => {
  const root = mkdtempSync(join(tmpdir(), "hanlintUsageJsonl-"));
  const corpus = join(root, "corpus");
  mkdirSync(corpus);
  const rows = [
    { source: "w1", text: `${SHARED}\n` },
    { source: "w2", text: `# 제목\n\n${SHARED}\n둘째 문장입니다.\n` },
  ];
  writeFileSync(join(corpus, "wiki.jsonl"), `${rows.map((row) => JSON.stringify(row)).join("\n")}\n`, "utf-8");
  assert.deepEqual([...readDocuments(corpus)].map(([source]) => source), ["w1", "w2"]);
  const result = buildIndex("wiki", readDocuments(corpus), root);
  const index = loadIndex("wiki", root);
  assert.deepEqual([result.documents, result.sentences], [2, 2]);
  assert.ok(index);
  assert.equal(index.search("임차료", 1)[0].documents, 2);
  assert.deepEqual(listIndexes(root).map((meta) => meta.kind), ["wiki"]);
});

test("collocations count neighbours by document", () => {
  const root = mkdtempSync(join(tmpdir(), "hanlintUsageColl-"));
  buildIndex("report", readDocuments(CORPUS), root);
  const index = loadIndex("report", root);
  assert.ok(index);
  const found = index.collocations("임차료");
  assert.ok(found);
  assert.equal(found.sampled, 3);
  assert.deepEqual(found.following, [["계약", 1]]);
  assert.deepEqual(found.predicates, [["줄어듭", 1]]);
  assert.equal(index.collocations("없는낱말"), null);
  assert.deepEqual(queryCores("임차료를 계약과 K-IFRS 12%"), ["임차료", "계약"]);
  assert.equal(predicateStem("감소하였습니다"), "감소");
  assert.equal(predicateStem("인식됩니다"), "인식");
  assert.equal(predicateStem("측정하며"), "측정");
  assert.equal(predicateStem("인식하지"), "인식");
  assert.equal(predicateStem("리스부채"), null);
  assert.equal(predicateStem("대하여"), "");
  assert.equal(predicateStem("또한"), null);
  assert.equal(predicateStem("기업회계기준서"), null);
  assert.equal(predicateStem("감소하며"), "감소");
  assert.equal(neighbourOf("기업회계기준서"), null);
  assert.deepEqual(neighbourOf("인식하지"), ["predicate", "인식"]);
  assert.deepEqual(neighbourOf("전년대비"), ["noun", "전년대비"]);
  for (const word of ["및", "따라", "중", "2025년", "대하여", "않아"]) assert.equal(neighbourOf(word), null, word);
});

test("bom and control characters read the same in both ports", () => {
  assert.deepEqual(sentencesOf("\ufeff# 제목입니다.\n첫째 문장입니다.\u001c둘째 문장입니다.\n"), ["첫째 문장입니다.", "둘째 문장입니다."]);
  assert.deepEqual(indexTokens("\ufeff회사는 창고를 \u0085씁니다."), ["회사", "창고", "씁니다", "씁니", "니다"]);
});

test("tiny index keeps common tokens", () => {
  const root = mkdtempSync(join(tmpdir(), "hanlintUsageTiny-"));
  buildIndex("report", [["one", "회사는 파주에 공장을 세웠습니다.\n"]], root);
  const index = loadIndex("report", root);
  assert.ok(index);
  assert.deepEqual(index.search("공장", 5).map((hit) => hit.text), ["회사는 파주에 공장을 세웠습니다."]);
});

test("varints decode what the builder wrote", () => {
  assert.deepEqual(decodeVarints(new Uint8Array([0, 1, 127, 128, 1, 172, 2, 255, 255, 3])), [0, 1, 127, 128, 300, 65535]);
});

test("build is deterministic, folds shared sentences, and search ranks", () => {
  const root = mkdtempSync(join(tmpdir(), "hanlintUsage-"));
  const first = buildIndex("report", readDocuments(CORPUS), join(root, "one"));
  const second = buildIndex("report", readDocuments(CORPUS), join(root, "two"));
  assert.deepEqual(first, second);
  assert.deepEqual(first, { documents: 3, sentences: 11, terms: 116 });
  for (const name of FILES) {
    assert.ok(readFileSync(join(root, "one", "report", name)).equals(readFileSync(join(root, "two", "report", name))), name);
  }
  const lines = readFileSync(join(root, "one", "report", "sentences.tsv"), "utf-8").split("\n");
  assert.equal(lines[0], `a001\t${SHARED}`);
  const documents = readFileSync(join(root, "one", "report", "documents.bin"));
  assert.equal(documents.readUInt32LE(0), 3);
  assert.equal(documents.length, 4 * 11);
  assert.ok(!lines.some((line) => line.includes("창고 임차 계약의 요약")), "제목은 문장이 아니다");
  const index = loadIndex("report", join(root, "one"));
  assert.ok(index);
  const hits = index.search("임차료 계약", 2);
  assert.deepEqual(hits.map((hit) => hit.text), [SHARED, "임차 부채는 이자만큼 늘고 낸 임차료만큼 줄어듭니다."]);
  assert.equal(hits[0].documents, 3);
  assert.equal(hits[0].source, "a001");
  assert.ok(hits[0].score > hits[1].score && hits[1].score > 0);
  assert.deepEqual(index.search("없는낱말", 5), []);
  assert.deepEqual(index.search("임차료 계약", 5), index.search("계약 임차료", 5));
  assert.equal(loadIndex("report", join(root, "none")), null);
  writeFileSync(join(root, "one", "report", "meta.json"), '{"format": 99}');
  assert.throws(() => loadIndex("report", join(root, "one")), /format/);
});

const CONVENTIONAL = "당사는 시장 상황에 대한 분석을 통해 대응 방안을 마련하였고 상기 계획을 이사회에서 정했습니다.";
const RARE = "그 계획은 이사회에 있어서 승인되었습니다.";

/** @param {string} text @param {Record<string, unknown>} mapping */
function dictionaryRules(text, mapping) {
  return lintText(text, configFromMapping(mapping))
    .filter((f) => f.rule === "translationese" || f.rule === "hardWord")
    .map((f) => `${f.rule}:${f.quote.split(" ")[0]}`);
}

test("report skips conventional dictionary entries", () => {
  assert.deepEqual(dictionaryRules(`${CONVENTIONAL}\n`, { preset: "report" }), []);
  assert.equal(dictionaryRules(`${CONVENTIONAL}\n`, { preset: "blog" }).length, 3);
  assert.deepEqual(dictionaryRules(`${RARE}\n`, { preset: "report" }), ["translationese:그"]);
  assert.notDeepEqual(dictionaryRules(`${CONVENTIONAL}\n`, { preset: "report", usageKind: "" }), []);
  assert.notDeepEqual(dictionaryRules(`${CONVENTIONAL}\n`, { preset: "report", usageShare: 1.01 }), []);
  assert.ok(conventional("translationese", "에 대한", "report", 0.9));
  assert.ok(!conventional("translationese", "에 있어서", "report", 0.9));
  assert.ok(conventional("translationese", "에 있어서", "report", 0.5));
  assert.equal(patternDocuments("translationese", "없는 항목", "report"), 0);
});

test("config dictionary entries are never conventional", () => {
  const mapping = { preset: "report", dictionary: { translationese: [{ pattern: "에 대한", fix: "의" }] } };
  assert.deepEqual(dictionaryRules("시장에 대한 분석입니다.\n", mapping), ["translationese:시장에"]);
});
