"""Pages 조립이 같은 코어를 담고 기존 작업 파일을 보존하는지 본다."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.derive.site import ROOT, buildSite


def testSiteContainsSameCoreAndCompleteData(tmp_path: Path) -> None:
    output = tmp_path / "site"
    buildSite(output)
    assert (output / "npm/src/index.js").read_bytes() == (ROOT / "npm/src/index.js").read_bytes()
    data = json.loads((output / "npm/data/siteData.json").read_text(encoding="utf-8"))
    assert data == {path.name: path.read_text(encoding="utf-8") for path in (ROOT / "npm/data").iterdir()}
    for name in ("index.html", "app.js", "worker.js", "style.css", "brand.svg", "guide.html", "license.html", ".nojekyll"):
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
