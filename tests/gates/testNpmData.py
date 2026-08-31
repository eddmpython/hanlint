"""npm/data 와 라이선스 고지는 파이썬 정본의 투영이다. 어긋나면 여기서 잡힌다."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.exportData import TARGET, render, staleFiles

ROOT = Path(__file__).resolve().parents[2]


def testNpmDataMatchesSource():
    files = render()
    assert "cliches.json" in files and "josa.txt" in files and "ruleDocs.json" in files
    assert "coverageTypes.txt" not in files
    assert TARGET.exists(), "npm/data 가 없다. python scripts/exportData.py 를 돌린다"
    assert not (TARGET / "coverageTypes.txt").exists()
    assert staleFiles(files) == []


def testNpmPackageDeclaresProjectedLicenses():
    sourceNotice = ROOT / "src" / "hanlint" / "data" / "koglType1.LICENSE.md"
    targetNotice = ROOT / "npm" / "koglType1.LICENSE.md"
    assert targetNotice.read_text(encoding="utf-8") == sourceNotice.read_text(encoding="utf-8")

    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))
    assert package["license"] == "SEE LICENSE IN koglType1.LICENSE.md"
    assert {"LICENSE", "koglType1.LICENSE.md"} <= set(package["files"])
