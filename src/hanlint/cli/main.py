"""명령줄 진입점.

```
hanlint                            인자가 없으면 첫 화면. 무엇을 칠 수 있는지 보인다
hanlint 글.md [다른.md ...]        검사. 서브커맨드 없이 파일이나 폴더만 주면 lint다. `-`는 stdin
hanlint watch 글.md                파일이 바뀔 때마다 다시 검사한다
hanlint fix 글.md                  기계가 고칠 수 있는 지적을 원문에 적용
hanlint audit 글.md                글에서 잰 값의 색 지도와 분포
hanlint map 글.md                  지도만
hanlint print 글.md                글에서 잰 값의 계층 JSON
hanlint rules                      규칙 목록을 묶음로 묶어서
hanlint explain <규칙>             규칙 설명
hanlint patterns --rule <규칙>     그 규칙을 피하는 문장 틀
hanlint primer --preset <종류>     쓰기 전에 읽는 한 장. 글쓰기 지침 일곱 줄과 켜진 규칙의 고치는 법, 예시 전후
hanlint spec --preset <종류>       쓰기 전에 볼 스펙
hanlint hook                       에이전트 훅. --prime은 쓰기 전 글쓰기 지침, 나머지는 쓴 마크다운의 비차단 검사
hanlint baseline 글들/             지금 있는 지적을 baseline 파일에 적는다. 그다음부터 새것만 막는다
hanlint doctor                     설정과 꺼진 규칙
hanlint init                       주석 달린 hanlint.toml. --output과 --preset blog|report|docs
hanlint profile build 글들/         승인된 글의 문체 분포. lint의 --profile로 견준다
hanlint coverage review.json 글.md 평가자 지적 가운데 hanlint가 같은 곳을 짚은 비율
hanlint diff 전.md 후.md           두 초안에서 잰 값의 차이
hanlint learn 전.md 후.md          실제 고침에서 승인할 패치와 치환 후보
hanlint packet 글.md              초안과 대조 자료와 고침 근거를 AI용 JSON으로
hanlint guard brief.json 글.md    구조화한 요구와 결과 글의 사실 대조
hanlint contract init 글.md      원문에서 최소 Reader Contract 초안
hanlint check contract.json 글.md 최소 Reader Contract 위반 결과 JSON
hanlint verify-patch ...           까닭이 붙은 그 자리만의 고침 검증
hanlint arena blind trial.json   기준과 후보의 안전 계약과 블라인드 선호 평가
hanlint arena panel trials.json  독자·사실 맥락과 다중 사람 합의가 있는 블라인드 평가
hanlint arena review-page ...    평가자 한 명의 네트워크 없는 단일 HTML 평가 화면
hanlint arena assignment-record  화면에서 받은 JSON의 배정과 좌우를 검증해 고정한다
hanlint arena judge-cases ...    자동 심사기의 좌우 위치 편향과 사람 합의 보정
hanlint blueprint brief.json     원문 없는 종류별 수사 구조 예산
hanlint evidence brief.json      사실마다 고정한 근거 목록 검증
hanlint entailment cases         정답 표시 없는 한국어 근거 함의 평가 사례
hanlint terms 글.md               한국어 학습자에게 처음 풀어 쓸 단어 후보
```

종료 코드는 0(지적 없음), 1(오류 있음), 2(파일이나 설정 문제)다. 경고만 있으면 0이다.
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
    blueprint,
    contract,
    coverage,
    diff,
    doctor,
    entailment,
    evidence,
    explain,
    fix,
    guard,
    hook,
    init,
    learn,
    lint,
    mapCommand,
    packet,
    patternsCommand,
    primer,
    printFingerprint,
    profile,
    rules,
    sheet,
    spec,
    terms,
    usage,
    watch,
)
from .commands import (
    check as checkCommand,
)
from .commands import (
    verifyPatch as verifyPatchCommand,
)
from .commands.shared import nearNames
from .help import rootHelp
from .welcome import welcome

COMMANDS = {
    "arena": arena,
    "blueprint": blueprint,
    "check": checkCommand,
    "contract": contract,
    "evidence": evidence,
    "entailment": entailment,
    "lint": lint,
    "fix": fix,
    "guard": guard,
    "hook": hook,
    "audit": audit,
    "map": mapCommand,
    "print": printFingerprint,
    "rules": rules,
    "explain": explain,
    "patterns": patternsCommand,
    "primer": primer,
    "spec": spec,
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
    "sheet": sheet,
    "usage": usage,
    "verify-patch": verifyPatchCommand,
}

ARGPARSE_WORDS = {
    "usage: ": "사용법: ",
    "positional arguments": "인자",
    "options": "옵션",
    "optional arguments": "옵션",
    "show this help message and exit": "이 도움말을 보이고 끝낸다",
    "show program's version number and exit": "버전을 보이고 끝낸다",
    "%(prog)s: error: %(message)s\n": "%(prog)s: 오류: %(message)s\n",
    "the following arguments are required: %s": "빠진 인자: %s",
    "unrecognized arguments: %s": "알 수 없는 인자: %s",
    "invalid choice: %(value)r (choose from %(choices)s)": "쓸 수 없는 값: %(value)r (쓸 수 있는 값: %(choices)s)",
    "argument %(argument_name)s: %(message)s": "%(argument_name)s: %(message)s",
    "expected one argument": "값 하나가 필요하다",
    "invalid %(type)s value: %(value)r": "%(type)s 값이 아니다: %(value)r",
}
"""argparse가 내는 영어 머리말과 오류의 한국어. argparse는 문구를 모듈의 `_`(gettext)로 고르므로 그 함수만 바꾼다. 파이썬 버전마다
문구가 조금 달라 표에 없는 문구는 영어 그대로 나온다."""


def useKoreanArgparse() -> None:
    argparse._ = lambda text: ARGPARSE_WORDS.get(text, text)  # type: ignore[attr-defined]


def buildParser() -> argparse.ArgumentParser:
    useKoreanArgparse()
    parser = argparse.ArgumentParser(prog="hanlint", description="한국어 글에서 규칙으로 잡을 수 있는 잘못을 찾는다")
    parser.add_argument("--version", action="version", version=f"hanlint {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    for name, module in COMMANDS.items():
        module.addParser(subparsers.add_parser(name, help=module.HELP))
    return parser


def looksLikeCommand(word: str) -> bool:
    """파일 이름이 아니라 서브커맨드를 치려던 것으로 보이나.

    실측: `hanlint rulez`가 `rulez를 찾지 못했다. 경로를 확인하거나`를 냈다. 파일 경로를 뒤지게
    만든 것이다. 확장자도 경로 구분자도 없는 아스키 한 단어이면 명령을 치려던 것으로 본다.
    """
    return bool(word) and word.isascii() and word.isalpha() and Path(word).suffix == "" and not Path(word).exists()


def normalizeArgv(argv: list[str]) -> list[str]:
    """서브커맨드 없이 파일이나 옵션만 주면 lint로 본다. `hanlint 글.md`가 첫 진입점이다.

    빈 인자는 여기서 다루지 않는다. `main`이 첫 화면으로 보낸다.
    """
    if argv[0] in COMMANDS or argv[0] in ("-h", "--help", "--version"):
        return argv
    if looksLikeCommand(argv[0]):
        near = nearNames(argv[0], list(COMMANDS))
        hint = f" 비슷한 이름: {', '.join(near)}." if near else ""
        raise ValueError(f"없는 명령: {argv[0]}.{hint} 전체 목록은 hanlint --help")
    return ["lint", *argv]


def useUtf8WhenPiped() -> None:
    """파이프와 리다이렉트로 나가는 출력은 UTF-8이다. 윈도우는 파이프에서 지역 코드 페이지를 쓰므로 고정한다."""
    for stream in (sys.stdout, sys.stderr):
        if not getattr(stream, "isatty", lambda: True)() and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    useUtf8WhenPiped()
    given = list(sys.argv[1:] if argv is None else argv)
    if not given:
        print(welcome(__version__))
        return 0
    if given in (["-h"], ["--help"]):
        print(rootHelp())
        return 0
    try:
        args = buildParser().parse_args(normalizeArgv(given))
        return COMMANDS[args.command].run(args)
    except FileNotFoundError as error:
        print(f"찾지 못한 파일: {error.filename}. 경로를 확인하거나 hanlint --help를 본다", file=sys.stderr)
        return 2
    except (ValueError, KeyError, RuntimeError) as error:
        print(str(error).strip("'"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
