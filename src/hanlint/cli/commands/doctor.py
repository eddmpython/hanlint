"""`hanlint doctor`. 지금 이 기계에서 무엇이 도는지 한 화면으로 답한다.

검사 결과가 뜻밖일 때 물을 것은 셋이다. 어느 설정을 읽었나, 어느 분석기로 돌았나, 어느 규칙이 꺼져
있나. 그 셋을 찾으려고 문서를 뒤지게 하지 않는다. 환경을 보고하는 명령이라 기계마다 값이 다르고,
그래서 두 구현의 글자 단위 동등성 게이트에는 넣지 않는다. 모양은 같고 값만 다르다.
"""

from __future__ import annotations

import argparse
import sys

from ... import __version__
from ...baseline import Baseline, load
from ...config import PRESETS
from ...rules import ruleNames
from .shared import SKIPPED_FOLDERS, addCommonOptions, configFrom, configLabel

HELP = "설정, 분석기, 꺼진 규칙을 한 화면에 보인다"


def addParser(parser: argparse.ArgumentParser) -> None:
    addCommonOptions(parser, ("text",), output=False)


def kiwiState() -> str:
    try:
        import kiwipiepy  # noqa: F401
    except ImportError:
        return "kiwi 는 없다 (pip install hanlint[kiwi] 로 형태소 정밀 모드를 켠다)"
    return "kiwi 를 쓸 수 있다 (--analyzer kiwi 또는 설정의 analyzer)"


def baselineState(config) -> str:
    """잠근 지적이 몇 건인지. baseline 이 빚을 감추는 자리가 되지 않게 늘 보인다."""
    if not config.baseline:
        return "없다 (hanlint baseline 글들/ 로 지금 지적을 잠근다)"
    try:
        found: Baseline = load(config.baseline)
    except (OSError, ValueError) as error:
        return f"{config.baseline} 를 못 읽었다: {error}"
    return f"{found.count}건이 {config.baseline} 에 잠겨 있다. 그 문장을 고치면 다시 나온다"


def run(args: argparse.Namespace) -> int:
    config = configFrom(args)
    names = ruleNames()
    off = config.offRules()
    lines = [
        f"hanlint {__version__}",
        "",
        f"파이썬    {sys.version.split()[0]}",
        f"설정      {configLabel(config)}",
        f"프리셋    {config.preset} ({', '.join(PRESETS)} 가운데)",
        f"분석기    {config.analyzer}. {kiwiState()}",
        f"규칙      {len(names) - len(off)}개 켜짐, {len(off)}개 꺼짐",
        f"잠금      {baselineState(config)}",
        f"폴더      점으로 시작하는 폴더와 {', '.join(SKIPPED_FOLDERS)} 는 건너뛴다. 직접 주면 검사한다",
    ]
    if off:
        lines.append(f"꺼진 규칙  {', '.join(off)}")
    lines.extend(
        [
            "",
            "다음: hanlint 글.md 로 검사한다. 설정이 기본값이면 hanlint init 으로 파일을 만든다",
        ]
    )
    print("\n".join(lines))
    return 0
