// @ts-check
import assert from "node:assert/strict";
import test from "node:test";

import { defaultConfig } from "../src/config/settings.js";
import { lintText } from "../src/index.js";
import { renderJson } from "../src/report/jsonReport.js";
import { renderText } from "../src/report/textReport.js";

/** @param {string} rule @param {string} text @param {import("../src/config/settings.js").Config} [config] */
function one(rule, text, config = defaultConfig()) {
  const found = lintText(text, config).find((finding) => finding.rule === rule);
  assert.ok(found);
  return found;
}

test("candidate rules publish useful choices and low-selection trials stay out", () => {
  const config = defaultConfig();
  config.longSentenceMax = 10;
  const long = one(
    "longSentence",
    "이 문장은 앞 사실을 길게 설명하고, 다음 사실은 주어를 다시 세워 아주 구체적으로 설명하며, 마지막 사실도 독자가 한 번에 읽기 어려울 만큼 여러 낱말을 더 붙이고 끝까지 이어 갑니다.",
    config,
  );
  assert.ok(long.candidates.length && long.candidates.every((candidate) => candidate.text.includes(" | ")));

  const deixis = one("danglingDeixis", "표를 만듭니다. 해당 값을 넣습니다.");
  assert.ok(deixis.candidates.some((candidate) => candidate.text === "표를 넣습니다."));

  const passive = one("doublePassive", "글이 쓰여져 있었다.");
  assert.equal(passive.fix, "글이 쓰여 있었다.");
  assert.deepEqual([passive.fragment, passive.replacement], ["져", ""]);
  assert.deepEqual(passive.candidates, []);

  const quotation = one("doublePassive", '문서에는 "결과가 저장되어집니다."라고 적혀 있습니다.');
  assert.equal(quotation.replacement, null);
  assert.deepEqual(quotation.candidates.map((candidate) => candidate.text), ['문서에는 "결과가 저장됩니다."라고 적혀 있습니다.']);

  assert.deepEqual(one("nounPile", "가상환경 생성 후 패키지 설치 확인 절차를 따릅니다.").candidates, []);
  assert.deepEqual(one("endingRepeat", "파일을 엽니다. 값을 넣습니다. 표를 만듭니다. 화면을 봅니다.").candidates, []);
});

test("json carries candidates and text puts them below exemplars", () => {
  const finding = one("danglingDeixis", "표를 만듭니다. 해당 값을 넣습니다.");
  const data = JSON.parse(renderJson(new Map([["글.md", [finding]]])));
  assert.deepEqual(data.files[0].findings[0].candidates[0], {
    text: "표를 넣습니다.",
    why: "바로 앞 문장에 나온 명사 `표`",
  });
  const text = renderText("글.md", [finding]);
  assert.ok(text.indexOf("본보기") < text.indexOf("후보 (기계가 고르지 않음)"));
  const noCandidate = JSON.parse(renderJson(new Map([["글.md", [one("cliche", "핵심은 속도입니다.")]]])));
  assert.ok(!("candidates" in noCandidate.files[0].findings[0]));
});
