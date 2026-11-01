"""사람이 읽는 hanlint 글에서 코드·영어 뒤에 조사를 띄어 쓰지 않는다.

한국어 맞춤법은 조사를 앞말에 붙인다. `README.md`를, `init`으로처럼 코드와 영어 뒤에서도 같다. 0.0.18까지 hanlint는
자기 문서, 규칙 설명, 사전의 까닭 글에서 `README.md` 를처럼 띄워 쓴 곳이 5,900곳이었고 붙여 쓴 곳도 2,800곳이라 한 도구
안에 두 꼴이 섞였다. primer와 hook --prime이 이 글을 AI 세션에 그대로 주므로 띄어쓰기가 다른 저장소의 글로 옮겨 갔다.
다시 생기지 않게 문서, 사전의 사람이 읽는 칸, 글쓰기 지침, 규칙 설명(ruleDocs.json)을 본다. 코드 블록 안은 보지 않고,
영어 뒤는 백틱 조각 밖에서만 본다(`앞에서 A 를 … B 를` 같은 틀은 일부러 띄운 인용이다).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JOSA = "을|를|은|는|이|가|의|에|에서|으로|로|와|과|도|만|이다|다"
AFTER_CODE = re.compile(rf"`[^`\n]+` ({JOSA})(?=[\s,.:;)]|$)")
AFTER_ENGLISH = re.compile(rf"(?<![\w/.\-\x00])[A-Za-z][A-Za-z0-9_\-]* ({JOSA})(?=[\s,.:;)]|$)")
CODE = re.compile(r"`[^`\n]+`")
FENCE = re.compile(r"^\s*(```|~~~)")
PROSE_KEYS = re.compile(r"\s*(why|moved|name|when|form|instead|source)\s*=")


def documents() -> list[Path]:
    data = ROOT / "src" / "hanlint" / "data"
    return [
        ROOT / "README.md",
        ROOT / "npm" / "README.md",
        *sorted((ROOT / "skills").rglob("*.md")),
        *sorted(data.glob("*.toml")),
        data / "koreanProse.txt",
        ROOT / "npm" / "data" / "ruleDocs.json",
    ]


def spaced(path: Path) -> list[str]:
    found = []
    inside = False
    name = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE.match(line):
            inside = not inside
            continue
        if inside or (path.suffix == ".toml" and not PROSE_KEYS.match(line)):
            continue
        masked = CODE.sub(lambda match: "\x00" * len(match.group(0)), line)
        hits = sorted([*AFTER_CODE.finditer(line), *AFTER_ENGLISH.finditer(masked)], key=lambda hit: hit.start())
        found += [f"{name}:{number}: {line[hit.start() : hit.end()]}" for hit in hits]
    return found


def testNoSpacedParticleAfterCodeOrEnglish() -> None:
    found = [item for path in documents() for item in spaced(path)]
    assert found == [], "\n".join(found[:40])


def testGateBites(tmp_path: Path) -> None:
    draft = tmp_path / "draft.md"
    draft.write_text(
        "`README.md` 를 연다. init 으로 만든다. `a`를 쓴다. `A 를 B`도 둔다.\n\n```\nREADME.md 를\n```\n", encoding="utf-8"
    )
    assert [item.split(": ", 1)[1] for item in spaced(draft)] == ["`README.md` 를", "init 으로"]
