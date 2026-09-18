"""저장소 안에 파이썬 바이트코드 캐시 (`__pycache__`) 가 없어야 한다.

규칙은 `python -X utf8 -B` 인데 어제 `-B` 없이 pytest 를 돌린 흔적 (2026-09-17 23:21 의 .pyc 여러 개) 이 src 와 tests
아래에 남았다. gitignore 라 트리에는 안 보여 아무도 몰랐다. conftest 의 `sys.dont_write_bytecode` 가 pytest 쪽 생성을 막고,
이 게이트가 CLI 나 스크립트를 `-B` 없이 돌린 잔해까지 잡는다. 음성 시험: 빈 `__pycache__` 폴더 하나를 tmp 코드 뿌리에
만들면 RED 다.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE_DIRS = ("src", "tests", "hooks", "scripts")


def cacheDirs(root: Path, dirs: tuple[str, ...]) -> list[str]:
    found = []
    for name in dirs:
        base = root / name
        if base.exists():
            found.extend(p.relative_to(root).as_posix() for p in base.rglob("__pycache__") if ".venv" not in p.parts)
    return sorted(found)


def testNoBytecodeCacheInsideRepository():
    found = cacheDirs(ROOT, CODE_DIRS)
    assert found == [], f"저장소 안에 __pycache__ 가 있다. -B 없이 파이썬을 돌린 흔적이다. 지우고 -B 로 돌린다: {found[:5]}"


def testGateSeesAStrayCache(tmp_path: Path):
    (tmp_path / "src" / "pkg" / "__pycache__").mkdir(parents=True)
    assert cacheDirs(tmp_path, ("src",)) == ["src/pkg/__pycache__"]
    assert cacheDirs(tmp_path, ("tests",)) == []
