// @ts-check
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { Contract, Patch, check, defaultConfig, ruleNames, verifyPatch } from "../src/index.js";

function contract() {
  return new Contract("배포를 결정할 운영자", "예산과 명세를 확인한다", [
    "예산은 380,000원이다.",
    "명세는 https://example.invalid/check 에 있다.",
    "확인 명령은 `mora check`다.",
  ]);
}

function surfaceConfig() {
  const config = defaultConfig();
  config.disable = new Set(ruleNames());
  return config;
}

const TEXT = "예산은 400,000원이다. 명세는 https://example.invalid/check 에 있다. `mora check`로 확인한다.";

test("check compiles protected atoms from the contract", () => {
  const result = check(TEXT, contract(), surfaceConfig()).asDict();
  assert.deepEqual(result.surface.missingNumbers, ["380000"]);
  assert.deepEqual(result.surface.unexpectedNumbers, ["400000"]);
  assert.equal(result.violationCount, 2);
  assert.equal(result.kind, "hanlint.checkResult");
});

test("patch must name and reduce an existing violation", () => {
  const result = verifyPatch(TEXT, new Patch("unexpectedNumbers", "400,000", "380,000"), contract(), surfaceConfig());
  assert.equal(result.verified, true);
  assert.ok(result.resultText.startsWith("예산은 380,000원"));
  assert.deepEqual(result.asDict().reason, { name: "unexpectedNumbers", before: 1, after: 0, reduced: true });
});

test("patch rejects unknown reasons and new protected atoms", () => {
  const unknown = verifyPatch(TEXT, new Patch("unknownRule", "400,000", "380,000"), contract(), surfaceConfig());
  assert.equal(unknown.verified, false);
  const changed = verifyPatch(TEXT, new Patch("unexpectedNumbers", "400,000", "500,000"), contract(), surfaceConfig());
  assert.equal(changed.verified, false);
  assert.deepEqual(changed.newSurfaceIssues, [["unexpectedNumbers", "500000"]]);
});

test("npm matches the published surface conformance suite", () => {
  const here = dirname(fileURLToPath(import.meta.url));
  const suite = JSON.parse(readFileSync(join(here, "..", "data", "readerContractConformanceV1.json"), "utf-8"));
  const selectedContract = Contract.fromMapping(suite.contract);
  const config = surfaceConfig();
  assert.equal(selectedContract.digest, suite.contractSha256);
  for (const item of suite.checks) {
    assert.deepEqual(check(item.text, selectedContract, config).asDict(), item.expected, item.id);
  }
  for (const item of suite.patches) {
    assert.deepEqual(verifyPatch(item.text, Patch.fromMapping(item.patch), selectedContract, config).asDict(), item.expected, item.id);
  }
});
