"""명령줄 진입점.

```
hanlint                            인자가 없으면 첫 화면. 무엇을 칠 수 있는지 보인다
hanlint 글.md [다른.md ...]        검사. 서브커맨드 없이 파일이나 폴더만 주면 lint 다. `-` 는 stdin
hanlint watch 글.md                파일이 바뀔 때마다 다시 검사한다
hanlint fix 글.md                  기계가 고칠 수 있는 지적을 원문에 적용
hanlint audit 글.md                지문 지도와 분포
hanlint map 글.md                  지도만
hanlint print 글.md                지문 계층 JSON
hanlint rules                      규칙 목록을 부류로 묶어서
hanlint explain <규칙>             규칙의 기술서
hanlint patterns --rule <규칙>     그 규칙을 피하는 문장 틀
hanlint baseline 글들/             지금 있는 지적을 잠근다. 그다음부터 새것만 막힌다
hanlint doctor                     설정과 꺼진 규칙
hanlint init                       주석 달린 hanlint.toml. --output 과 --preset blog|report|docs
hanlint profile build 글들/         승인된 글의 문체 분포. lint 의 --profile 로 견준다
hanlint coverage review.json 글.md 평가자 지적 가운데 hanlint 가 같은 자리를 집은 비율
hanlint diff 전.md 후.md           두 초안의 지문 차이
hanlint learn 전.md 후.md          실제 고침에서 승인할 정확 패치와 표면 치환 후보
hanlint packet 글.md              초안과 대조 자료와 고침 근거를 AI용 JSON으로
hanlint guard brief.json 글.md    구조화 요구와 결과의 사실 표면 계약
hanlint arena blind trial.json   기준과 후보의 안전 계약과 블라인드 선호 평가
hanlint terms 글.md               한국어 학습자에게 처음 풀어 쓸 낱말 후보
```

종료 코드는 0 (지적 없음), 1 (error 지적 있음), 2 (파일이나 설정 문제) 다. notice 만 있으면 0 이다.
게이트에 물릴 수 있게 한 것이지 글의 합격을 판정한 것이 아니다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .. import __version__
from .commands import (
    arena,
    audit,
    baselineCommand,
    coverage,
    diff,
    doctor,
    explain,
    fix,
    guard,
    init,
    learn,
    lint,
    mapCommand,
    packet,
    patternsCommand,
    printFingerprint,
    profile,
    rules,
    terms,
    watch,
)
from .commands.shared import nearNames
from .welcome import welcome

COMMANDS = {
    "arena": arena,
    "lint": lint,
    "fix": fix,
    "guard": guard,
    "audit": audit,
    "map": mapCommand,
    "print": printFingerprint,
    "rules": rules,
    "explain": explain,
    "patterns": patternsCommand,
    "doctor": doctor,
    "watch": watch,
    "baseline": baselineCommand,
    "init": init,
    "profile": profile,
    "coverage": coverage,
    "diff": diff,
    "learn": learn,
    "packet": packet,
    "terms": terms,
}


def buildParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hanlint", description="한국어 글에서 반복되는 결함을 결정적으로 잡는다")
    parser.add_argument("--version", action="version", version=f"hanlint {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    for name, module in COMMANDS.items():
        module.addParser(subparsers.add_parser(name, help=module.HELP))
    return parser


def looksLikeCommand(word: str) -> bool:
    """파일 이름이 아니라 서브커맨드를 치려던 것으로 보이나.

    실측: `hanlint rulez` 가 `rulez 를 찾지 못했다. 경로를 확인하거나` 를 냈다. 파일 경로를 뒤지게
    만든 것이다. 확장자도 경로 구분자도 없는 아스키 한 낱말이면 명령을 치려던 것으로 본다.
    """
    return bool(word) and word.isascii() and word.isalpha() and Path(word).suffix == "" and not Path(word).exists()


def normalizeArgv(argv: list[str]) -> list[str]:
    """서브커맨드 없이 파일이나 옵션만 주면 lint 로 본다. `hanlint 글.md` 가 첫 진입점이다.

    빈 인자는 여기서 다루지 않는다. `main` 이 첫 화면으로 보낸다.
    """
    if argv[0] in COMMANDS or argv[0] in ("-h", "--help", "--version"):
        return argv
    if looksLikeCommand(argv[0]):
        near = nearNames(argv[0], list(COMMANDS))
        hint = f" 가까운 이름: {', '.join(near)}." if near else ""
        raise ValueError(f"{argv[0]} 는 모르는 명령이다.{hint} 전체 목록은 hanlint --help")
    return ["lint", *argv]


def useUtf8WhenPiped() -> None:
    """파이프와 리다이렉트로 나가는 출력은 UTF-8 이다. 윈도우는 파이프에서 지역 코드 페이지를 쓰므로 고정한다."""
    for stream in (sys.stdout, sys.stderr):
        if not getattr(stream, "isatty", lambda: True)() and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    useUtf8WhenPiped()
    given = list(sys.argv[1:] if argv is None else argv)
    if not given:
        print(welcome(__version__))
        return 0
    try:
        args = buildParser().parse_args(normalizeArgv(given))
        return COMMANDS[args.command].run(args)
    except FileNotFoundError as error:
        print(f"{error.filename} 를 찾지 못했다. 경로를 확인하거나 hanlint --help", file=sys.stderr)
        return 2
    except (ValueError, KeyError, RuntimeError) as error:
        print(str(error).strip("'"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
