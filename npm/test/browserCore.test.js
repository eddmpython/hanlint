import test from "node:test";
import assert from "node:assert/strict";
import { createHash, randomBytes } from "node:crypto";
import { sha256 } from "../src/digest.js";
import { configFromMapping, inspectText, learnText, lintText, compareRevision, contractFromTextV2, check } from "../src/index.js";

test("브라우저 SHA-256은 경계 길이와 UTF-8에서 Node와 같다", () => {
  for (const size of [0, 1, 55, 56, 63, 64, 65, 119, 120, 128, 1024, 10000]) {
    for (const text of ["가😀é".repeat(size), randomBytes(size).toString("hex")]) {
      assert.equal(sha256(text), createHash("sha256").update(text).digest("hex"));
    }
  }
  assert.equal(sha256("abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
});

test("편집기 보고서는 같은 지적과 문맥 본보기를 제공한다", () => {
  const config = configFromMapping({ preset: "report" });
  const text = "가상환경 생성 후 패키지 설치 확인 절차를 따릅니다. 결과가 저장되어집니다.";
  const result = inspectText(text, config);
  assert.deepEqual(result.findings, lintText(text, config));
  assert.equal(result.report.findings.length, result.findings.length);
  assert.ok(result.report.findings.find((item) => item.rule === "doublePassive").exemplar.after);
});

test("수정 후보는 같은 규칙이 남거나 문장 대응이 모호하면 기권한다", () => {
  assert.ok(learnText("설계에 대한 이해가 필요합니다.", "설계를 알아야 합니다.").exemplars.some((item) => item.rule === "translationese"));
  assert.deepEqual(learnText("설계에 대한 이해가 필요합니다.", "새 설계에 대한 이해가 필요합니다.").exemplars, []);
  assert.deepEqual(learnText("설계에 대한 이해가 필요합니다. 결과를 기록합니다.", "설계를 알아야 합니다. 결과는 표에 적습니다. 담당자가 검토합니다.").exemplars, []);
  assert.deepEqual(learnText("2개가 있습니다.", "3개가 있습니다.").operations, []);
  assert.equal(learnText("첫 렌더 결과입니다.", "첫 렌더링 결과입니다.").operations[0].after, "렌더링");
});

test("자유 원고 비교는 빈 글과 반복 제목도 받고 같은 표면 검사를 쓴다", () => {
  assert.equal(compareRevision("", "").outline.matches, true);
  assert.equal(compareRevision("원고가 저장되어집니다.", "원고가 저장됩니다.").outline.matches, true);
  assert.equal(compareRevision("", "## 새 제목").outline.matches, false);
  const repeated = "## 제목\n\n본문\n\n## 제목\n\n다른 본문";
  assert.equal(compareRevision(repeated, repeated).outline.matches, true);
  assert.equal(compareRevision(repeated, repeated.replace("다른 본문", "## 추가 제목")).outline.matches, false);
  const source = "## 예산\n\n예산 380,000원, `save()`와 https://example.com/spec 을 확인한다.";
  const revised = source.replace("380,000", "400,000").replace("## 예산", "## 비용");
  const receipt = check(revised, contractFromTextV2(source, "글쓴이", "원문을 다듬는다"));
  const comparison = compareRevision(source, revised);
  assert.deepEqual(comparison.changes, receipt.surface);
  assert.deepEqual(comparison.outline, receipt.outline);
  assert.deepEqual(compareRevision("\u1100\u1173\u11af `변수`", "글 `변수`").changes.unexpectedCode, []);
  assert.throws(() => contractFromTextV2("제목 없는 글", "글쓴이", "원문을 다듬는다"), /outline.headings/);
});
