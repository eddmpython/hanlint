"""Pages 조립이 같은 코어를 담고 기존 작업 파일을 보존하는지 본다."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from scripts.derive.site import ROOT, buildSite


def testSiteContainsSameCoreAndCompleteData(tmp_path: Path) -> None:
    output = tmp_path / "site"
    buildSite(output)
    assert (output / "npm/src/index.js").read_bytes() == (ROOT / "npm/src/index.js").read_bytes()
    data = json.loads((output / "npm/data/siteData.json").read_text(encoding="utf-8"))
    assert data == {path.name: path.read_text(encoding="utf-8") for path in (ROOT / "npm/data").iterdir()}
    for name in ("index.html", "app.js", "worker.js", "style.css", "brand.png", "guide.html", "license.html", ".nojekyll"):
        assert (output / name).is_file()
    assert not (output / "node_modules").exists()
    assert not (output / "package.json").exists()
    assert (output / "pretendard.woff2").read_bytes() == (ROOT / "web/pretendard.woff2").read_bytes()
    assert "SIL OPEN FONT LICENSE" in (output / "license.html").read_text(encoding="utf-8")
    assert (output / "theme.js").read_bytes() == (ROOT / "web/theme.js").read_bytes()


def testSiteRefusesExistingOutputWithoutChangingIt(tmp_path: Path) -> None:
    sentinel = tmp_path / "original.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="비어 있어야"):
        buildSite(tmp_path)
    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert list(tmp_path.iterdir()) == [sentinel]


def testSiteRefusesOutputInsideRepository() -> None:
    with pytest.raises(ValueError, match="저장소 밖"):
        buildSite(ROOT / "web")


def testBrowserBulkFixLeavesNoticesForReview(tmp_path: Path) -> None:
    """편집기 일괄 고침은 CLI처럼 error만 적용하고 notice는 사용자가 직접 고른다."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 가 없다")
    output = tmp_path / "site"
    buildSite(output)
    for source in (ROOT / "npm/data").iterdir():
        shutil.copy2(source, output / "npm/data" / source.name)
    (output / "package.json").write_text('{"type":"module"}', encoding="utf-8")
    script = """
import assert from "node:assert/strict";
import { configFromMapping, inspectText } from "./npm/src/index.js";
import { renderFindings } from "./views.js";

const nodes = new Map();
function makeNode() {
  return { dataset: {}, append() {}, replaceChildren() {}, addEventListener() {} };
}
globalThis.document = {
  getElementById(id) { if (!nodes.has(id)) nodes.set(id, makeNode()); return nodes.get(id); },
  createElement() { return makeNode(); },
  createTextNode() { return makeNode(); },
};
const config = configFromMapping({ preset: "blog" });
const noticeText = "피드백을 남깁니다.";
const mixedText = "피드백을 남깁니다. 결과가 저장되어집니다.";
const notice = inspectText(noticeText, config);
const mixed = inspectText(mixedText, config);
assert.ok(notice.findings.some((item) => item.rule === "hardWord" && item.severity === "notice"));
assert.ok(notice.findings.every((item) => item.severity !== "error"));
assert.ok(mixed.findings.some((item) => item.rule === "doublePassive" && item.severity === "error"));
const handlers = { reject() {}, patch() {}, fix() {}, locate() {} };
renderFindings(notice, handlers);
assert.equal(nodes.get("fixAllButton").disabled, true);
renderFindings(mixed, handlers);
assert.equal(nodes.get("fixAllButton").disabled, false);

const messages = [];
globalThis.self = { postMessage(message) { messages.push(message); } };
await import("./worker.js");
function fix(text, index) {
  const id = messages.length + 1;
  self.onmessage({ data: { id, action: "fix", text, original: text, preset: "blog", patches: [], index } });
  const reply = messages.at(-1);
  assert.equal(reply.id, id);
  assert.equal(reply.error, undefined);
  return reply.result.text;
}
assert.equal(fix(noticeText, null), noticeText);
assert.equal(fix(mixedText, null), "피드백을 남깁니다. 결과가 저장됩니다.");
assert.equal(fix(noticeText, notice.findings.findIndex((item) => item.rule === "hardWord")), "의견을 남깁니다.");
"""
    result = subprocess.run(
        [node, "--input-type=module", "-e", script], cwd=output, capture_output=True, text=True, encoding="utf-8"
    )
    assert result.returncode == 0, result.stderr
