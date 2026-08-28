// @ts-check
/** 마크다운 블록 경계. 파이썬 tests/document/testParseMarkdown.py 와 같은 사례다. */
import assert from "node:assert/strict";
import test from "node:test";

import { dropFences, fenceLanguage, parseMarkdown } from "../src/document/parseMarkdown.js";

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

test("dropFences removes only named languages and renumbers", () => {
  const text = "## 절\n\n```course-scene\nrole: open\n```\n\n설명.\n\n```python\nprint(1)\n```\n\n```Course-Scene extra\nrole: close\n```\n";
  const doc = parseMarkdown(text);
  assert.deepEqual(doc.blocks.map((block) => block.kind), ["heading", "code", "prose", "code", "code"]);
  assert.deepEqual(doc.blocks.filter((block) => block.kind === "code").map((block) => fenceLanguage(block.text)), ["course-scene", "python", "course-scene"]);
  const dropped = dropFences(doc, ["course-scene"]);
  assert.deepEqual(dropped.blocks.map((block) => block.kind), ["heading", "prose", "code"]);
  assert.deepEqual(dropped.blocks.map((block) => block.index), [0, 1, 2]);
  assert.deepEqual(dropped.blocks.map((block) => block.startLine), [1, 7, 9]);
  assert.deepEqual(dropped.sections[dropped.sections.length - 1].blocks.map((block) => block.kind), ["prose", "code"]);
  assert.deepEqual(dropped.ignored.map((block) => block.startLine), [3, 13]);
  assert.equal(dropFences(doc, []), doc);
  assert.equal(dropFences(doc, ["mermaid"]), doc);
});

test("dropFences keeps inline controls on their original lines", () => {
  const text = "<!-- hanlint-disable-next imperativePeriod -->\n\n```course-scene\nrole: open\n```\n\n파일을 열어 보세요.\n";
  const doc = parseMarkdown(text);
  assert.deepEqual(doc.disabled, [["imperativePeriod", 3, 5]]);
  const dropped = dropFences(doc, ["course-scene"]);
  assert.deepEqual(dropped.disabled, doc.disabled);
  assert.deepEqual(dropped.blocks.map((block) => block.kind), ["html", "prose"]);
});

test("link-only paragraph is an embed", () => {
  const text = "설명.\n\n[영상](https://www.youtube.com/watch?v=x \"캡션\")\n\n[문서](https://x)를 읽습니다.\n\n[문서](https://x) 참고.\n";
  const doc = parseMarkdown(text);
  assert.deepEqual(doc.blocks.map((block) => block.kind), ["prose", "embed", "prose", "prose"]);
  const wrapped = parseMarkdown("[감사 설정](https://x)\n의 구성은 다르다.\n");
  assert.deepEqual(wrapped.blocks.map((block) => block.kind), ["prose"]);
});

test("indented list paragraph is prose but deeper code is code", () => {
  const text = "1. 단계입니다.\n\n    목록 안 설명입니다.\n\n        result: ok\n\n목록 밖입니다.\n";
  const doc = parseMarkdown(text);
  assert.deepEqual(doc.blocks.map((block) => block.kind), ["list", "prose", "code", "prose"]);
  assert.deepEqual(doc.blocks.filter((block) => block.kind === "prose").map((block) => block.text), ["    목록 안 설명입니다.", "목록 밖입니다."]);
});
