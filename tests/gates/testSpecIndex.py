"""specs 폴더의 README 색인이 실제 파일과 맞는지 본다.

색인은 손으로 적는 라우팅이라 파일을 더하고 색인을 잊으면 조용히 어긋난다. 2026-08-31 에
`skills/specs/operation/README.md` 가 나흘 전부터 있던 verify.md, release.md, feedback.md 를 빼놓고
"코어가 생기면서 같은 커밋에 만든다" 고 적고 있었다. 링크가 가리키는 파일이 실제로 있는지도 본다.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INDEXES = sorted((ROOT / "skills" / "specs").glob("*/README.md"))
LINK = re.compile(r"\]\(([^)#]+\.md)\)")


def testThereAreSpecFolders():
    assert INDEXES, "skills/specs 아래 README 색인을 못 찾았다"


@pytest.mark.parametrize("index", INDEXES, ids=lambda path: path.parent.name)
def testIndexListsEverySpecBesideIt(index: Path):
    linked = {(index.parent / target).resolve() for target in LINK.findall(index.read_text(encoding="utf-8"))}
    present = {path.resolve() for path in index.parent.glob("*.md") if path.name != "README.md"}
    missing = sorted(path.name for path in present - linked)
    assert not missing, f"{index.parent.name}/README.md 색인에 없는 문서: {missing}"


@pytest.mark.parametrize("index", INDEXES, ids=lambda path: path.parent.name)
def testEveryIndexLinkExists(index: Path):
    dead = sorted(target for target in LINK.findall(index.read_text(encoding="utf-8")) if not (index.parent / target).exists())
    assert not dead, f"{index.parent.name}/README.md 의 죽은 링크: {dead}"
