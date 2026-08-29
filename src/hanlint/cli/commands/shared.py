"""명령들이 함께 쓰는 인자와 준비."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ...config import DEFAULT_PRESET, PRESET_NAMES, Config, loadConfig
from ...data import patternsAvoiding
from ...edit import applyFixes
from ...rules import Finding, ruleNames

FORMATS = ("text", "json", "github", "html", "compact")
SEVERITIES = ("all", "error", "notice")
NEAR_LIMIT = 3
"""오타에 가까운 이름을 몇 개까지 보이는가. 넷을 넘으면 목록을 보는 것이 낫다."""
NEAR_PREFIX = 3
"""앞 몇 글자가 같으면 가까운 이름으로 보는가."""
STDIN = "-"
STDIN_NAME = "<stdin>"
MARKDOWN = (".md", ".markdown")
"""폴더를 주면 이 확장자만 찾는다. 글 폴더에 섞여 있는 이미지와 설정을 검사하지 않는다."""

SKIPPED_FOLDERS = ("node_modules",)
"""폴더를 훑을 때 안 들어가는 이름. 점으로 시작하는 폴더도 함께 건너뛴다.

**왜 있는가.** 실측: 블로그 저장소 모양 (내 글 2편, node_modules 패키지 150개, .git 과 .venv 안에도
마크다운) 에서 `hanlint .` 이 파일 156개를 훑어 error 305건을 냈다. 내 글은 출력 3435줄 가운데 3338줄째,
97% 지점에 처음 나왔다. 그 305건은 남이 쓴 영어 README 의 것이고 내 글의 수가 아니다. 더 나쁜 것은
`hanlint fix .` 이 npm 과 pip 가 소유한 파일을 실제로 덮어썼다는 것이다.

**목록을 키우지 않는다.** 점 폴더와 `node_modules` 둘로 끝낸다. `venv`, `dist`, `build`, `vendor`,
`target` 을 하나씩 더하기 시작하면 끝이 없고 언어마다 다르다. 그 둘이 실측 사례를 덮고, 나머지는
건너뛴 것을 알려 주는 줄을 본 사용자가 폴더를 좁혀서 푼다.

**명시가 규칙을 이긴다.** 파일이나 폴더를 직접 주면 이 목록과 무관하게 검사한다."""


def isSkipped(name: str) -> bool:
    """폴더 이름 하나가 건너뛸 것인가. 점으로 시작하거나 목록에 있으면 건너뛴다."""
    return name.startswith(".") or name in SKIPPED_FOLDERS


def markdownUnder(folder: Path) -> list[str]:
    """폴더 아래 마크다운. 건너뛸 폴더에는 안 들어간다. 경로 문자열 순이라 두 판이 같은 차례를 낸다.

    경로 문자열로 정렬한다. Path 끼리의 비교는 윈도에서 대소문자를 무시해 npm 판과 갈린다.
    """
    found: list[str] = []
    for child in sorted(folder.iterdir(), key=lambda p: p.name):
        if child.is_dir():
            if not isSkipped(child.name):
                found.extend(markdownUnder(child))
        elif child.suffix.lower() in MARKDOWN:
            found.append(str(child))
    return sorted(found)


def addCommonOptions(parser: argparse.ArgumentParser, formats: tuple[str, ...] = ("text", "json"), output: bool = True) -> None:
    """설정과 출력 꼴 옵션. `output` 은 그 명령이 실제로 파일로 쓸 수 있을 때만 켠다.

    받아 놓고 안 쓰는 옵션은 거짓말이다. 특히 `--output` 은 조용히 무시되면 사용자가 기다리던 파일이
    안 생긴다 (실측: rules, doctor, fix, watch 넷이 그랬다). 그래서 emit 을 부르는 명령만 받는다.
    `--no-color` 는 아직 색이 없는 출력에서도 받는다. 스크립트가 관례로 붙이는 것을 막을 이유가 없고
    무시돼도 잃는 것이 없다.
    """
    parser.add_argument("--config", type=Path, help="설정 파일. 없으면 hanlint.toml 이나 pyproject.toml 을 찾는다")
    parser.add_argument(
        "--preset",
        choices=PRESET_NAMES,
        help="글의 종류. 설정 파일 없이 이번 실행에만 정한다. 기본은 설정이나 blog",
    )
    parser.add_argument(
        "--disable", action="append", default=[], metavar="RULE", help="이번 실행에서 끌 규칙. 여러 번 줄 수 있다"
    )
    parser.add_argument("--format", choices=formats, default=formats[0], help=f"출력 꼴. 기본 {formats[0]}")
    if output:
        addOutputOption(parser)
    parser.add_argument("--no-color", dest="noColor", action="store_true", help="색을 끈다")
    parser.add_argument("--quiet", action="store_true", help="설정 출처 줄을 뺀다")


def addOutputOption(parser: argparse.ArgumentParser) -> None:
    """`--output`. 이 옵션을 받는 명령은 반드시 `emit` 으로 그 값을 쓴다."""
    parser.add_argument("--output", type=Path, help="출력을 파일로 쓴다")


def addSeverityOptions(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--severity", choices=SEVERITIES, default="all", help="보여 줄 지적. 기본 all")
    parser.add_argument("--errors-only", dest="errorsOnly", action="store_true", help="--severity error 와 같다")


def severityOf(args: argparse.Namespace) -> str:
    if getattr(args, "errorsOnly", False):
        return "error"
    return getattr(args, "severity", "all")


def keep(findings: list[Finding], severity: str) -> list[Finding]:
    if severity == "all":
        return findings
    return [f for f in findings if f.severity == severity]


def nearNames(query: str, names: list[str]) -> list[str]:
    """오타에 가까운 이름. 부분 문자열이 먼저, 앞 글자가 같은 것이 다음이다. 이름 순으로 끊는다."""
    lowered = query.lower()
    scored: list[tuple[int, str]] = []
    for name in names:
        low = name.lower()
        if lowered in low or low in lowered:
            scored.append((0, name))
        elif low[:NEAR_PREFIX] == lowered[:NEAR_PREFIX]:
            scored.append((1, name))
    return [name for _, name in sorted(scored)][:NEAR_LIMIT]


def checkDisabled(config: Config) -> None:
    """`disable` 에 없는 규칙 이름이 있으면 멈춘다.

    실측: `--disable 없는규칙` 이 조용히 지나갔고 `hanlint doctor` 는 그것을 꺼진 규칙으로 세어
    `꺼진 규칙 ..., 없는규칙` 이라고 확인해 줬다. 껐다고 믿은 규칙이 계속 잡히는데 도구는 껐다고 말한다.
    `preset` 은 이미 모르는 값을 거절한다. 규칙 이름만 예외일 이유가 없다.
    """
    names = ruleNames()
    unknown = sorted(set(config.disable) - set(names))
    if not unknown:
        return
    near = nearNames(unknown[0], names)
    hint = f" 가까운 이름: {', '.join(near)}." if near else ""
    raise ValueError(f"모르는 규칙 이름: {', '.join(unknown)}.{hint} 목록은 hanlint rules --names")


def configFrom(args: argparse.Namespace, start: Path | None = None) -> Config:
    config = loadConfig(args.config, start=start)
    if getattr(args, "preset", None):
        config.preset = args.preset
    config.disable |= set(getattr(args, "disable", []) or [])
    checkDisabled(config)
    return config


def configLabel(config: Config) -> str:
    """출력 첫 줄에 적을 설정 출처. 현재 폴더 아래면 상대 경로, 아니면 그대로."""
    if config.source is None:
        return "기본값"
    try:
        relative = os.path.relpath(config.source)
    except ValueError:
        return config.source
    return config.source if relative.startswith("..") else relative


def header(config: Config) -> str:
    """설정 출처와 지금 도는 프리셋. 기본 프리셋이면 이름을 빼서 줄이 길어지지 않게 한다."""
    where = configLabel(config)
    return f"설정: {where}" if config.preset == DEFAULT_PRESET else f"설정: {where}, 프리셋 {config.preset}"


def summary(results: dict[str, list[Finding]]) -> str:
    """글에 실제로 있는 수. **거른 뒤가 아니라 거르기 전을 센다.**

    실측: error 2건짜리 글에 `--severity notice` 를 붙이면 요약이 `error 0` 이라고 적었다. 보여 줄 것을
    고르는 옵션이 있는 것을 없다고 말하게 만들고 있었다. 다음 걸음도 같은 이유로 `error 0` 이라며
    사람과 LLM 평가로 보냈다. 무엇을 보여 줄지와 무엇이 있는지는 다른 질문이다.
    """
    errors = sum(1 for findings in results.values() for f in findings if f.severity == "error")
    notices = sum(1 for findings in results.values() for f in findings if f.severity == "notice")
    return f"파일 {len(results)}개, error {errors}, notice {notices}"


def commonest(findings: list[Finding]) -> str:
    """가장 많이 난 규칙. 같은 수면 이름 순으로 갈라 같은 입력에 같은 답이 나온다.

    실측: 다섯 편에 error 15건이 나왔을 때 알파벳 첫 규칙은 cliche (2건) 였고 실제로 가장 많은 것은
    noQuestion (4건) 이었다. 한 줄뿐인 다음 걸음이 가장 작은 더미를 가리키고 있었다.
    """
    counted: dict[str, int] = {}
    for finding in findings:
        counted[finding.rule] = counted.get(finding.rule, 0) + 1
    return min(counted, key=lambda rule: (-counted[rule], rule))


def fixableCount(texts: dict[str, str], results: dict[str, list[Finding]]) -> int:
    """`hanlint fix` 가 실제로 고칠 error 수. 고침이 달렸다는 것과 자리를 잡을 수 있다는 것은 다르다.

    실측: `그러면 `에 있어서` 를 봅니다` 에서 다음 걸음은 `1건은 hanlint fix 가 바로 고친다` 라고 했는데
    fix 는 `0곳 고침, 1곳 건너뜀` 을 냈다. 조각이 백틱 안이라 원문에서 자리를 못 잡은 것이다. 약속과
    실제가 갈리면 사람은 lint 와 fix 를 무한히 왕복한다. 그래서 세는 쪽이 실제로 고치는 함수를 부른다.
    """
    total = 0
    for name, findings in results.items():
        text = texts.get(name)
        if text is None:
            continue
        errors = [f for f in findings if f.severity == "error"]
        total += len(applyFixes(text, errors).applied)
    return total


def nextStep(results: dict[str, list[Finding]], fixable: int = 0) -> str:
    """검사 끝에 붙는 다음 행동 한 줄. 합격을 판정하지 않고 지금 무엇을 하면 되는지만 말한다.

    `fixable` 은 `fixableCount` 가 낸 실제로 고쳐질 수다. 부르는 쪽이 원문을 들고 있을 때만 준다.
    """
    findings = [f for found in results.values() for f in found]
    errors = [f for f in findings if f.severity == "error"]
    notices = len(findings) - len(errors)
    if errors:
        rule = commonest(errors)
        if fixable:
            return f"다음: error {len(errors)}건 가운데 {fixable}건은 hanlint fix 가 바로 고친다. 나머지는 손으로 고친다"
        if patternsAvoiding(rule):
            return f"다음: error {len(errors)}건을 고친다. 다시 쓸 틀은 hanlint patterns --rule {rule}"
        return f"다음: error {len(errors)}건을 고친다. 규칙이 왜 있는지는 hanlint explain {rule}"
    if notices:
        return f"다음: error 0. 확인할 자리 {notices}건을 읽고 판단한 뒤 사람과 LLM 평가로 넘어간다"
    return "다음: 세어서 잡히는 결함이 없다. 좋은 글이라는 뜻은 아니므로 사람과 LLM 평가로 넘어간다"


def isStdin(path: Path | str) -> bool:
    return str(path) == STDIN


def collectFiles(paths: list) -> list[str]:
    """폴더를 주면 그 아래 마크다운을 이름 순으로 편다. 파일과 `-` 는 그대로 둔다."""
    found: list[str] = []
    for path in paths:
        if isStdin(path):
            found.append(STDIN)
            continue
        candidate = Path(path)
        if candidate.is_dir():
            inside = markdownUnder(candidate)
            if not inside:
                raise ValueError(
                    f"{path} 안에 마크다운 파일이 없다. 점으로 시작하는 폴더와 node_modules 는 건너뛴다. "
                    "그 안을 보려면 그 폴더를 직접 준다"
                )
            found.extend(inside)
            continue
        found.append(str(path))
    return found


def readInput(path: Path | str, stdinName: str = STDIN_NAME) -> tuple[str, str]:
    """(이름, 본문). `-` 면 stdin 을 UTF-8 로 읽는다.

    폴더를 주면 말로 막는다. 실측: `hanlint audit 글들/` 이 폴더를 파일로 열어 파이썬 PermissionError
    트레이스백을 뱉었다. 지문 지도와 계층 JSON 은 글 하나를 보는 화면이라 폴더를 받지 않는다.
    """
    if isStdin(path):
        return stdinName, sys.stdin.buffer.read().decode("utf-8")
    return str(path), readFile(Path(path))


def startFolder(paths: list) -> Path:
    """설정을 찾기 시작할 폴더. 첫 실제 파일의 폴더, 전부 stdin 이면 현재 폴더."""
    for path in paths:
        if not isStdin(path):
            return Path(path).resolve().parent
    return Path.cwd()


def readFile(path: Path) -> str:
    """글 하나를 읽는다. 폴더를 주면 말로 막는다.

    실측: `hanlint audit 글들/` 이 폴더를 파일로 열어 파이썬 PermissionError 트레이스백을 뱉었다.
    지문 지도와 계층 JSON 과 초안 비교는 글 하나를 보는 화면이라 폴더를 받지 않는다. 폴더를 받는 것은
    lint 와 fix 와 baseline 이고 그것들은 collectFiles 를 지난다.
    """
    if path.is_dir():
        raise ValueError(f"{path} 는 폴더다. 이 명령은 글 하나를 본다. 폴더는 hanlint 와 hanlint fix 가 받는다")
    return path.read_text(encoding="utf-8")


def emit(text: str, output: Path | None) -> None:
    if output is None:
        print(text)
        return
    output.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
    print(f"{output} 에 썼다", file=sys.stderr)


def colorEnabled(args: argparse.Namespace) -> bool:
    if getattr(args, "noColor", False) or getattr(args, "output", None) is not None:
        return False
    return bool(getattr(sys.stdout, "isatty", lambda: False)())
