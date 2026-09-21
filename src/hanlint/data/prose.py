"""쓰기 전에 읽는 작법서. 정본은 koreanProse.txt 하나다.

`hanlint primer` 는 절마다 한 줄로 펴서 첫머리에 싣고, `hanlint hook --prime` 은 본문을 그대로 에이전트 문맥에
넣는다. 두 자리가 같은 파일을 읽으므로 작법서를 고치면 둘이 같이 바뀐다. 이 본문을 읽고 쓴 글이 읽지 않고 쓴
글을 블라인드 심판 96건에서 이겼다. 필자가 claude-opus-5 일 때 67 대 29 (tests/_attempts/craftLift), Codex
(gpt-5.6-sol) 일 때 90 대 6 (tests/_attempts/codexCraft) 이다.
"""

from __future__ import annotations

from .load import readText

PROSE = "koreanProse.txt"


def proseGuide() -> str:
    """작법서 본문. 끝의 줄바꿈 하나까지 파일 그대로다."""
    return readText(PROSE)


def proseSections() -> tuple[tuple[str, str], ...]:
    """(제목, 본문) 짝. 첫 짝은 문서 제목과 첫머리이고 나머지는 일곱 줄이다. 제목의 `#` 는 뗀다."""
    sections: list[tuple[str, list[str]]] = []
    for line in proseGuide().splitlines():
        if line.startswith("#"):
            sections.append((line.lstrip("#").strip(), []))
        elif sections:
            sections[-1][1].append(line)
    return tuple((title, "\n".join(body).strip()) for title, body in sections)
