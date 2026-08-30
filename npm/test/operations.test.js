// @ts-check
import assert from "node:assert/strict";
import test from "node:test";

import { configFromMapping } from "../src/config/settings.js";
import {
  applyOperation,
  operationFor,
  operationFromApproval,
  protectedAtoms,
  projectOperations,
} from "../src/data/operations.js";
import { fingerprint, lintText } from "../src/index.js";
import { renderJson } from "../src/report/jsonReport.js";

function renderOperation() {
  const operation = operationFromApproval("첫 렌더 결과입니다.", "첫 렌더링 결과입니다.", ["docs"]);
  assert.ok(operation);
  return operation;
}

test("approval becomes one bounded surface operation", () => {
  const operation = renderOperation();
  assert.deepEqual(operation, { before: "렌더", after: "렌더링", presets: ["docs"] });
  assert.equal(applyOperation("두 번째 렌더 결과입니다.", operation), "두 번째 렌더링 결과입니다.");
});

test("application abstains at word protected and ambiguous positions", () => {
  const operation = renderOperation();
  for (const source of [
    "프리렌더 결과입니다.",
    "이미 렌더링 결과입니다.",
    "렌더 뒤 렌더 결과입니다.",
    "`렌더` 결과입니다.",
    "https://example.com/렌더 결과입니다.",
    "[문서](https://example.com/렌더) 결과입니다.",
  ]) {
    assert.equal(applyOperation(source, operation), undefined, source);
  }
});

test("extraction rejects meaning and protected fact changes", () => {
  assert.equal(operationFromApproval("이것은 결과입니다.", "이는 결과입니다.", ["docs"]), undefined);
  assert.equal(operationFromApproval("2개가 있습니다.", "3개가 있습니다.", ["docs"]), undefined);
  assert.equal(operationFromApproval("`run`을 씁니다.", "`runs`를 씁니다.", ["docs"]), undefined);
  assert.equal(operationFromApproval("주소는 https://a.example 입니다.", "주소는 https://b.example 입니다."), undefined);
  assert.equal(operationFromApproval("원인을 확인합니다.", "결과에 따라 다시 확인합니다."), undefined);
  assert.equal(operationFromApproval("서울 지점입니다.", "서을 지점입니다.", ["docs"], ["서울"]), undefined);
  assert.ok(protectedAtoms("v2의 `run`은 https://a.example/x.py를 씁니다.").length);
});

test("protected URLs stop before markdown and sentence punctuation", () => {
  const linked = protectedAtoms("[https://a.example/x](https://a.example/x)");
  assert.equal(linked.filter((atom) => atom === "url:https://a.example/x").length, 2);
  assert.ok(linked.includes("link:https://a.example/x"));
  assert.ok(protectedAtoms("주소는 https://a.example.").includes("url:https://a.example"));
});

test("selection and configuration require one safe operation", () => {
  const first = renderOperation();
  const second = { before: "결과입니다", after: "결괏값입니다", presets: ["docs"] };
  assert.ok(operationFor("렌더 결과입니다.", "docs", [first]));
  assert.equal(operationFor("렌더 결과입니다.", "blog", [first]), undefined);
  assert.equal(operationFor("렌더 결과입니다.", "docs", [first], ["렌더"]), undefined);
  assert.equal(operationFor("렌더 결과입니다.", "docs", [first, second]), undefined);

  const entry = { before: "여러가지", after: "여러 가지", presets: ["blog"] };
  const operations = projectOperations([entry], ["blog", "docs"]);
  assert.equal(applyOperation("여러가지 방법입니다.", operations[0]), "여러 가지 방법입니다.");
  for (const invalid of [
    [entry, entry],
    [{ ...entry, presets: [] }],
    [{ ...entry, presets: ["unknown"] }],
    [{ ...entry, before: "이것은", after: "이는" }],
    [{ ...entry, before: "버전 2", after: "버전 3" }],
    [{ ...entry, extra: true }],
  ]) {
    assert.throws(() => projectOperations(invalid, ["blog", "docs"]));
  }
});

test("json report carries an operation and exact patch keeps priority", () => {
  const text = "첫 렌더 결과입니다.";
  const config = configFromMapping({ operations: [{ before: "렌더", after: "렌더링", presets: ["blog"] }] });
  const document = fingerprint(text, config, "글.md");
  const data = JSON.parse(
    renderJson(
      new Map([["글.md", lintText(text, config, "글.md")]]),
      null,
      null,
      config.preset,
      [],
      new Map([["글.md", document]]),
      [],
      config.operations,
    ),
  );
  assert.equal(data.files[0].operations[0].operation.result, "첫 렌더링 결과입니다.");

  const source = "핵심은 렌더입니다.";
  const priorityConfig = configFromMapping({
    patches: [
      {
        rule: "cliche",
        before: source,
        after: "렌더링에는 3초가 걸립니다.",
        moved: "결과를 직접 씀",
        cue: "핵심은",
        reader: "new",
        presets: ["blog"],
      },
    ],
    operations: [{ before: "렌더", after: "렌더링", presets: ["blog"] }],
  });
  const priorityDoc = fingerprint(source, priorityConfig, "글.md");
  const priorityFindings = lintText(source, priorityConfig, "글.md");
  const priority = JSON.parse(
    renderJson(
      new Map([["글.md", priorityFindings]]),
      null,
      null,
      priorityConfig.preset,
      [],
      new Map([["글.md", priorityDoc]]),
      priorityConfig.patches,
      priorityConfig.operations,
    ),
  );
  assert.ok(!("operations" in priority.files[0]));
  assert.ok(priority.files[0].findings.some((finding) => "patch" in finding));
});
