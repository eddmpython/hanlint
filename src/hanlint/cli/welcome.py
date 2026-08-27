"""`hanlint` 를 인자 없이 쳤을 때의 첫 화면.

전에는 argparse 가 `the following arguments are required: files` 를 뱉었다. 그것은 오류이지 안내가
아니다. 처음 쓰는 사람이 보는 화면은 무엇을 하는 도구인지, 지금 무엇을 칠 수 있는지, 이 폴더에서
바로 해 볼 것이 무엇인지를 답해야 한다. 그래서 세 가지만 담는다.

npm 판 (`npm/src/cli/main.js`) 이 같은 글자를 낸다. 같은 폴더에서 두 판을 돌리면 결과가 같다.
"""

from __future__ import annotations

from pathlib import Path

MARKDOWN = (".md", ".markdown")
SAMPLE_LIMIT = 3
"""현재 폴더에서 예시로 보일 파일 수. 넷을 넘으면 목록이 안내를 밀어낸다."""


def nearbyMarkdown(folder: Path) -> list[str]:
    """현재 폴더 바로 아래의 마크다운. 이름 순이라 같은 폴더면 두 판이 같은 것을 고른다."""
    try:
        names = sorted(p.name for p in folder.iterdir() if p.suffix.lower() in MARKDOWN and p.is_file())
    except OSError:
        return []
    return names[:SAMPLE_LIMIT]


def welcome(version: str, folder: Path | None = None) -> str:
    folder = folder or Path.cwd()
    nearby = nearbyMarkdown(folder)
    example = nearby[0] if nearby else "글.md"
    shown = [
        (f"hanlint {example}", "검사한다. 자리와 이유와 고칠 말이 나온다"),
        (f"hanlint fix {example}", "기계가 확실히 고칠 수 있는 자리를 원문에 적용한다"),
        (f"hanlint audit {example}", "글의 모양을 지도와 분포로 본다"),
    ]
    width = max(len(command) for command, _ in shown)
    lines = [
        f"hanlint {version}  한국어 글에서 세면 확정되는 결함을 집는다. 좋은 글인지는 판정하지 않는다",
        "",
        *(f"  {command:<{width}}  {why}" for command, why in shown),
    ]
    if nearby:
        lines.extend(["", f"이 폴더의 마크다운: {', '.join(nearby)}. 폴더를 통째로 줘도 된다 (hanlint .)"])
    else:
        lines.extend(["", "이 폴더에는 마크다운이 없다. 파일 하나나 폴더 하나를 인자로 준다"])
    lines.extend(
        [
            "",
            "처음이면 hanlint init 으로 설정을 만든다. 글의 종류가 블로그가 아니면 --preset report 나 --preset docs",
            "규칙 목록은 hanlint rules, 규칙 하나가 왜 있는지는 hanlint explain <규칙>, 지금 상태는 hanlint doctor",
            "전체 사용법은 hanlint --help",
        ]
    )
    return "\n".join(lines)
