"""`hanlint init`. 주석 달린 hanlint.toml을 만든다. 규칙마다 한 줄 설명이 붙어 있어 끄고 켤 것을 바로 정한다.

`--preset`이 글의 종류를 정한다. 참고 문서에 독자 호출 규칙이 도는 것 같은 자리를 이름 하나로 없앤다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ...config import PRESET_NAMES, PRESETS, Config
from ...rules import CATEGORY_TITLES, ruleCategories, ruleNames, ruleSummary

HELP = "주석 달린 hanlint.toml을 만든다"
THRESHOLD_FIELDS = (
    "fragmentRun",
    "introMaxParagraphs",
    "headingUniformRatio",
    "headingSentenceMaxLevel",
    "bridgeRepeatMin",
    "nounPileMin",
    "endingRun",
    "factListMinSentences",
    "factListMaxMeanLength",
    "flowValleyMinSentences",
    "longSentenceMax",
    "duplicateBlockRatio",
    "firstResultMaxParagraphs",
    "introMaxImages",
    "moreLaterMaxChars",
    "tableOddCellMinRows",
)


def addParser(parser: argparse.ArgumentParser) -> None:
    # `--output`이다. `--path`는 다른 명령에서 stdin으로 넣은 글의 이름을 뜻하므로 한 단어이 두 가지를
    # 뜻하지 않게 했다. 부르는 쪽이 이름만 보고 무엇을 넘길지 맞힐 수 있어야 한다.
    parser.add_argument("--output", type=Path, default=Path("hanlint.toml"), help="만들 파일. 기본 hanlint.toml")
    parser.add_argument(
        "--preset", choices=PRESET_NAMES, default="blog", help="글의 종류. 그 종류에 안 맞는 규칙을 처음부터 끈다"
    )
    parser.add_argument("--force", action="store_true", help="이미 있으면 덮어쓴다")


def render(preset: str = "blog") -> str:
    defaults = Config()
    categories = ruleCategories()
    lines = [
        "# hanlint 설정. 규칙을 끄려면 disable에 이름을 넣는다. 규칙 설명은 hanlint explain <규칙>으로 본다.",
        "",
        "# 글의 종류. 그 종류에 안 맞는 규칙을 처음부터 끈다. disable은 그 위에 더한다.",
    ]
    for name, off in PRESETS.items():
        lines.append(f"#   {name}: {', '.join(off) if off else '전부 켠다'}")
    lines.extend([f'preset = "{preset}"', "", "# 규칙 목록과 한 줄 설명"])
    for category, title in CATEGORY_TITLES.items():
        inside = [name for name in ruleNames() if categories[name] == category]
        if not inside:
            continue
        lines.append(f"#  {title}")
        for name in inside:
            lines.append(f"#   {name}: {ruleSummary(name)}")
    lines.extend(
        [
            "",
            "disable = []",
            "",
            "# 대표 검색어를 읽을 frontmatter 필드. 없으면 keywordMissing은 돌지 않는다",
            '# keywordField = "primaryKeyword"',
            "",
            "# 도입과 마지막 절이 담아야 하는 frontmatter 필드. 비어 있으면 fieldEcho는 돌지 않는다",
            '# introFields = ["readerQuestion"]',
            '# endingFields = ["readerTakeaway"]',
            "",
            "# hanlint profile build가 만든 파일. 있으면 글 종류의 기본 프로파일 대신 이 파일과 비교한다(outsideProfile)",
            '# profile = "profile.json"',
            "",
            "# hanlint baseline이 만든 기준 파일. 있으면 그 안의 지적은 보이지 않고 새로 생긴 지적만 막는다",
            '# baseline = ".hanlint-baseline.json"',
            "",
            "# 코드도 산문도 아닌 펜스의 언어 이름. 이 펜스는 코드 블록으로 세지 않고 검사에서도 뺀다",
            '# ignoreFences = ["course-scene", "mermaid"]',
            "",
            "# 기준값. 아래 값이 기본값이다",
        ]
    )
    for name in THRESHOLD_FIELDS:
        lines.append(f"# {name} = {getattr(defaults, name)}")
    lines.extend(
        [
            "",
            "# 용례. 그 종류의 실제 글에 흔한 명사 연쇄(nounPile)와 사전 표현은 짚지 않는다. 명사 연쇄는 usageMin편 이상의",
            "# 문서에 나온 것, 사전 표현은 문서의 usageShare 비율 이상에 나온 것(사업보고서의 `에 대한`)이다.",
            "# 종류는 프리셋이 정한다 (report만 있다). 빈 문자열이면 어떤 프리셋에서도 용례를 보지 않는다",
            '# usageKind = ""',
            "# usageMin = 3",
            "# usageShare = 0.9",
            "",
            "# 사전에 더할 항목. 키는 cliches, translationese, redundantPair, japaneseLoan, easyWords,",
            "# screenSentence, screenNarration, screenTone, screenWord, calqueFrame",
            "# [dictionary]",
            '# cliches = ["우리의 여정"]',
            '# translationese = [{ pattern = "에 대한 이해", fix = "를 아는 것" }]',
            "",
            "# 자동 고침이 건드리지 말아야 할 한국어 고유명사와 프로젝트 용어. 숫자와 영문 식별자는 저절로 지킨다",
            '# protectedTerms = ["한린트", "김민지"]',
            '# enforceStyle = ["noQuestion", "nounPile"]  # 고른 문체 규칙만 오류로 낸다',
            "",
            "# 사람이 승인한 프로젝트 예시. 같은 규칙과 프리셋의 기본 예시 대신 쓴다",
            "# [[exemplars]]",
            '# rule = "translationese"',
            '# before = "설계에 대한 이해가 필요합니다."',
            '# after = "설계를 알아야 합니다."',
            '# moved = "명사구를 서술어로 풀어 썼다"',
            '# presets = ["blog"]',
            "",
            "# 사람이 승인한 그 자리만의 고침. 원문을 포함해 조건이 모두 맞을 때만 그대로 적용한다",
            "# [[patches]]",
            '# rule = "translationese"',
            '# before = "설계에 대한 이해가 필요합니다."',
            '# after = "설계를 알아야 합니다."',
            '# moved = "명사구를 서술어로 풀어 썼다"',
            '# sourceText = "설계에 대한 이해가 필요합니다."  # before의 마크다운까지 보존한 선택용 원문',
            '# sentence = "설계에 대한 이해가 필요합니다."  # before에서 마크다운 표식을 걷은 선택용 원문',
            '# cue = "에 대한"',
            '# reader = "new"',
            '# presets = ["blog"]',
            "",
            "# 사람이 적용 범위까지 승인한 글자 바꾸기. 단어 경계가 맞고 숫자·링크·코드가 그대로일 때만 바꾼다",
            "# [[operations]]",
            '# before = "여러가지"',
            '# after = "여러 가지"',
            '# presets = ["blog"]',
            "",
        ]
    )
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    if args.output.exists() and not args.force:
        raise ValueError(f"이미 있는 파일: {args.output}. 덮어쓰려면 --force를 붙인다")
    args.output.write_text(render(args.preset), encoding="utf-8", newline="\n")
    off = PRESETS[args.preset]
    tail = f"{args.preset} 프리셋은 규칙 {len(off)}개를 끈다" if off else f"{args.preset} 프리셋은 규칙을 전부 켠다"
    print(f"만들었다: {args.output}. {tail}. 더 끄려면 disable에 이름을 넣는다")
    return 0
