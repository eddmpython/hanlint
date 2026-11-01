"""`hanlint doctor`. 지금 이 기계에서 무엇이 도는지 한 화면으로 답한다.

검사 결과가 뜻밖일 때 물을 것은 둘이다. 어느 설정을 읽었나, 어느 규칙이 꺼져 있나. 그 둘을 찾으려고 문서를
뒤지게 하지 않는다. 환경을 보고하는 명령이라 기계마다 값이 다르고, 그래서 두 구현의 글자 단위 동등성 게이트에는
넣지 않는다. 모양은 같고 값만 다르다.
"""

from __future__ import annotations

import argparse
import sys

from ... import __version__
from ...baseline import Baseline, load
from ...config import PRESETS
from ...rules import ruleNames
from .shared import SKIPPED_FOLDERS, addCommonOptions, configFrom, configLabel

HELP = "설정과 꺼진 규칙을 한 화면에 보인다"


def addParser(parser: argparse.ArgumentParser) -> None:
    addCommonOptions(parser, ("text",), output=False)


def baselineState(config) -> str:
    """잠근 지적이 몇 건인지. baseline이 빚을 감추는 자리가 되지 않게 늘 보인다."""
    if not config.baseline:
        return "없음 (만들려면 hanlint baseline 글들/)"
    try:
        found: Baseline = load(config.baseline)
    except (OSError, ValueError) as error:
        return f"읽지 못했다: {config.baseline} ({error})"
    return f"{config.baseline}에 지적 {found.count}건이 들어 있다. 그 문장을 고치면 다시 나온다"


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
        f"규칙      {len(names) - len(off)}개 켜짐, {len(off)}개 꺼짐",
        f"기준 파일 {baselineState(config)}",
        f"폴더      건너뛰는 것: 점으로 시작하는 폴더, {', '.join(SKIPPED_FOLDERS)}. 직접 주면 검사한다",
    ]
    if off:
        lines.append(f"꺼진 규칙  {', '.join(off)}")
    lines.extend(
        [
            "",
            "다음: hanlint 글.md로 검사한다. 설정 파일이 없으면 hanlint init으로 만든다",
        ]
    )
    print("\n".join(lines))
    return 0
