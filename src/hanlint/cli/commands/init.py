"""`hanlint init`. 주석 달린 hanlint.toml 을 만든다. 규칙마다 한 줄 설명이 붙어 있어 끄고 켤 것을 바로 정한다."""

from __future__ import annotations

import argparse
from pathlib import Path

from ...config import Config
from ...rules import ruleNames, ruleSummary

HELP = "주석 달린 hanlint.toml 을 만든다"
THRESHOLD_FIELDS = (
    "fragmentRun",
    "introMaxParagraphs",
    "headingUniformRatio",
    "nounPileMin",
    "endingRun",
    "factListMinSentences",
    "factListMaxMeanLength",
    "topicBreakMinSentences",
    "longSentenceMax",
)


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--path", type=Path, default=Path("hanlint.toml"), help="만들 파일. 기본 hanlint.toml")
    parser.add_argument("--force", action="store_true", help="이미 있으면 덮어쓴다")


def render() -> str:
    defaults = Config()
    lines = [
        "# hanlint 설정. 규칙을 끄려면 disable 에 이름을 넣는다. 규칙의 기술서는 hanlint explain <규칙>.",
        "",
        "# 규칙 목록과 한 줄 설명",
    ]
    for name in ruleNames():
        lines.append(f"#   {name}: {ruleSummary(name)}")
    lines.extend(
        [
            "",
            "disable = []",
            "",
            "# surface 는 의존성 0 기본, kiwi 는 pip install hanlint[kiwi] 가 있을 때",
            f'analyzer = "{defaults.analyzer}"',
            "",
            "# 대표 검색어를 읽을 frontmatter 필드. 없으면 keywordMissing 은 돌지 않는다",
            '# keywordField = "primaryKeyword"',
            "",
            "# hanlint profile build 가 만든 파일. 있으면 참조 글과의 편차 구간을 notice 로 더한다",
            '# profile = "profile.json"',
            "",
            "# 임계. 기본값의 정본은 hanlint 의 config/settings.py 다",
        ]
    )
    for name in THRESHOLD_FIELDS:
        lines.append(f"# {name} = {getattr(defaults, name)}")
    lines.extend(
        [
            "",
            "# 사전에 더할 항목. 키는 cliches, translationese, redundantPair, japaneseLoan",
            "# [dictionary]",
            '# cliches = ["우리의 여정"]',
            '# translationese = [{ pattern = "에 대한 이해", fix = "를 아는 것" }]',
            "",
        ]
    )
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    if args.path.exists() and not args.force:
        raise ValueError(f"{args.path} 가 이미 있다. 덮어쓰려면 --force")
    args.path.write_text(render(), encoding="utf-8")
    print(f"{args.path} 를 만들었다. 규칙을 끄려면 disable 에 이름을 넣는다")
    return 0
