"""명령줄 진입점.

```
hanlint 글.md [다른.md ...]        검사. 서브커맨드 없이 파일만 주면 lint 다
hanlint audit 글.md                지문 지도와 분포
hanlint map 글.md                  지도만
hanlint print 글.md                지문 계층 JSON
hanlint rules                      규칙 목록
hanlint explain <규칙>             규칙의 기술서
hanlint init                       주석 달린 hanlint.toml
hanlint profile build 글들/         승인된 글의 문체 분포. lint 의 --profile 로 견준다
```

종료 코드는 0 (지적 없음), 1 (error 지적 있음), 2 (파일이나 설정 문제) 다. notice 만 있으면 0 이다.
게이트에 물릴 수 있게 한 것이지 글의 합격을 판정한 것이 아니다.
"""

from __future__ import annotations

import argparse
import sys

from .. import __version__
from .commands import audit, explain, init, lint, mapCommand, printFingerprint, profile, rules

COMMANDS = {
    "lint": lint,
    "audit": audit,
    "map": mapCommand,
    "print": printFingerprint,
    "rules": rules,
    "explain": explain,
    "init": init,
    "profile": profile,
}


def buildParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hanlint", description="한국어 글에서 반복되는 결함을 결정적으로 잡는다")
    parser.add_argument("--version", action="version", version=f"hanlint {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    for name, module in COMMANDS.items():
        module.addParser(subparsers.add_parser(name, help=module.HELP))
    return parser


def normalizeArgv(argv: list[str]) -> list[str]:
    """서브커맨드 없이 파일이나 옵션만 주면 lint 로 본다. `hanlint 글.md` 가 첫 진입점이다."""
    if not argv:
        return ["lint"]
    if argv[0] in COMMANDS or argv[0] in ("-h", "--help", "--version"):
        return argv
    return ["lint", *argv]


def main(argv: list[str] | None = None) -> int:
    parser = buildParser()
    args = parser.parse_args(normalizeArgv(list(sys.argv[1:] if argv is None else argv)))
    try:
        return COMMANDS[args.command].run(args)
    except FileNotFoundError as error:
        print(f"{error.filename} 를 찾지 못했다. 경로를 확인하거나 hanlint --help", file=sys.stderr)
        return 2
    except (ValueError, KeyError, RuntimeError) as error:
        print(str(error).strip("'"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
