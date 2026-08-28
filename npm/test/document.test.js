// @ts-check
/** 마크다운 블록 경계. 파이썬 tests/document/testParseMarkdown.py 와 같은 사례다. */
import assert from "node:assert/strict";
import test from "node:test";

import { parseMarkdown } from "../src/document/parseMarkdown.js";

test("inline triple backticks do not open a fence", () => {
  const text = "```kubectl -A```\n\n```bash\n# 셸 주석이다\nkubectl get pods\n```\n";
  const doc = parseMarkdown(text);
  assert.deepEqual(doc.blocks.map((block) => block.kind), ["prose", "code"]);
});

test("indented code and quote are not prose", () => {
  const text = "설명.\n\n    root 1 ...\n    root 2 ...\n\n> 인용은 ... 그대로 둔다.\n";
  const doc = parseMarkdown(text);
  assert.deepEqual(doc.blocks.map((block) => block.kind), ["prose", "code", "quote"]);
});

test("indented list paragraph is prose but deeper code is code", () => {
  const text = "1. 단계입니다.\n\n    목록 안 설명입니다.\n\n        result: ok\n\n목록 밖입니다.\n";
  const doc = parseMarkdown(text);
  assert.deepEqual(doc.blocks.map((block) => block.kind), ["list", "prose", "code", "prose"]);
  assert.deepEqual(doc.blocks.filter((block) => block.kind === "prose").map((block) => block.text), ["    목록 안 설명입니다.", "목록 밖입니다."]);
});
