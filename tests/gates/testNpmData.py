"""npm/data 는 파이썬 정본의 투영이다. 정본을 고치고 투영을 안 돌리면 여기서 잡힌다."""

from __future__ import annotations

from scripts.exportData import TARGET, render, staleFiles


def testNpmDataMatchesSource():
    files = render()
    assert "cliches.json" in files and "josa.txt" in files and "ruleDocs.json" in files
    assert TARGET.exists(), "npm/data 가 없다. python scripts/exportData.py 를 돌린다"
    assert staleFiles(files) == []
