import assert from "node:assert/strict";
import test from "node:test";

import { defaultConfig } from "../src/config/settings.js";
import { renderWritingSpec, writingSpec } from "../src/report/writingSpec.js";

function row(spec, rowId) {
  return spec.rows.find((item) => item.id === rowId);
}

test("프로파일 관찰값과 켜진 규칙을 한 사양으로 편다", () => {
  const config = defaultConfig();
  config.preset = "blog";
  const spec = writingSpec(config, "합니다", 800);

  assert.equal(spec.profile, "blog");
  assert.equal(row(spec, "amount").guidance, "문단 6개, 문단마다 문장 2~4개, 문장 11개 안팎");
  assert.deepEqual(row(spec, "sentenceLength").basis, ["profile.blog.sentence.length", "rule.longSentence"]);
  assert.match(row(spec, "nounRun").guidance, /5개부터 nounPile이 지적/);
  assert.match(renderWritingSpec(spec), /^hanlint spec  blog 종류, 합니다체, 800자\./);
});

test("꺼진 규칙을 사양의 요구라고 말하지 않는다", () => {
  const config = defaultConfig();
  config.preset = "report";
  config.disable = new Set(["longSentence", "nounPile"]);
  const spec = writingSpec(config, "한다");

  assert.deepEqual(row(spec, "sentenceLength").basis, ["profile.report.sentence.length"]);
  assert.doesNotMatch(row(spec, "sentenceLength").guidance, /longSentence/);
  assert.match(row(spec, "question").guidance, /^규칙 요구 없음/);
});

test("프로파일이 없는 대화 프리셋은 사양을 꾸며 내지 않는다", () => {
  const config = defaultConfig();
  config.preset = "chat";
  assert.throws(() => writingSpec(config), /종류 프로파일이 없어/);
});
