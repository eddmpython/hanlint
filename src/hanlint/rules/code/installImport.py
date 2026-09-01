from __future__ import annotations

import re
from collections.abc import Iterator
from functools import cache

from ...config import Config
from ...data import loadLines
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, NOTICE, Finding
from ..registry import rule

# 캡처는 백틱과 한글에서 멈춘다. 패키지 이름에 한글은 없고, 산문 문장에서는 지문이 백틱을 이미 걷어
# 내므로 한글이 유일한 경계다. 안 멈추면 `pip install kubernetes` 뒤의 산문까지 삼켜 python, client,
# library 를 설치된 패키지로 등록하고 그 이름을 import 하는 코드를 조용히 통과시킨다 (2026-08-31).
INSTALL = re.compile(r"(?:pip\s+install|uv\s+add|uv\s+pip\s+install|conda\s+install|poetry\s+add)\s+([^\n#|&;`가-힣]+)")
IMPORT = re.compile(r"^\s*(?:import\s+([\w.]+(?:\s*,\s*[\w.]+)*)|from\s+([\w.]+)\s+import\b)")
REQUIREMENT = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[([^\]]*)\])?")


@cache
def stdlib() -> frozenset[str]:
    return frozenset(loadLines("pythonStdlib.txt"))


@cache
def packageOf() -> dict[str, frozenset[str]]:
    mapping = {}
    for line in loadLines("pythonPackages.txt"):
        module, _, package = line.partition("\t")
        mapping[module] = frozenset(normalize(name) for name in package.split("|"))
    return mapping


@cache
def hiddenDeps() -> tuple[tuple[re.Pattern[str], str, str], ...]:
    found = []
    for line in loadLines("hiddenDeps.txt"):
        pattern, requirement, why = line.split("\t")
        found.append((re.compile(pattern), requirement, why))
    return tuple(found)


def normalize(name: str) -> str:
    return name.lower().replace("_", "-")


def installed(doc: DocumentPrint) -> dict[str, set[str]] | None:
    """설치 줄이 말한 패키지 → extras. 설치 줄이 하나도 없으면 None."""
    texts = [line for block in doc.codeBlocks for _, line in block.lines] + [s.text for s in doc.sentences]
    packages: dict[str, set[str]] = {}
    seen = False
    for text in texts:
        for match in INSTALL.finditer(text):
            seen = True
            for token in match.group(1).split():
                token = token.strip("\"'`")
                if token.startswith("-") or not token:
                    continue
                requirement = REQUIREMENT.match(token)
                if not requirement:
                    continue
                name = normalize(requirement.group(1))
                extras = {normalize(e.strip()) for e in (requirement.group(2) or "").split(",") if e.strip()}
                packages.setdefault(name, set()).update(extras)
    return packages if seen else None


def localModules(doc: DocumentPrint) -> set[str]:
    """글이 만드는 .py 파일 이름. 그 모듈은 설치할 것이 아니다."""
    names = set()
    for sentence in doc.sentences:
        names.update(m.group(1) for m in re.finditer(r"\b(\w+)\.py\b", sentence.text))
    for block in doc.codeBlocks:
        for _, line in block.lines:
            names.update(m.group(1) for m in re.finditer(r"\b(\w+)\.py\b", line))
    return names


@rule("installImport", mechanism="contrast")
def installImport(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """설치 줄에 없는 패키지를 import 하는 코드. 그리고 코드 한 줄이 조용히 요구하는 숨은 의존성.

    왜: 독자는 글이 시킨 설치 줄만 실행한다. 목록에 없는 패키지는 ModuleNotFoundError 로 끝나고 extra 가 빠진
        백엔드는 실행 중에 멈춘다.
    어디서: 실측. 블로그 004 가 ibis-framework[duckdb] 만 설치하고 sqlite 엔진에 붙었고 사람 평가자가 집었다.
        모듈과 패키지 이름의 대응은 data/pythonPackages.txt, 표준 라이브러리는 data/pythonStdlib.txt, 숨은
        의존성은 data/hiddenDeps.txt.
    고치기: 설치 줄에 그 패키지 (필요하면 extra 까지) 를 더한다.
    안 잡는 것: 설치 줄이 하나도 없는 글 (판단할 수 없다). 표준 라이브러리. 글이 만드는 .py 파일. 상대 import.
        숨은 의존성은 notice 로 낸다.
    """
    packages = installed(doc)
    if packages is None:
        return
    local = localModules(doc)
    for block in doc.codeBlocks:
        if block.language not in ("python", "py"):
            continue
        for line, code in block.lines:
            match = IMPORT.match(code)
            if match:
                modules = [m.strip() for m in (match.group(1) or match.group(2)).split(",")]
                for module in modules:
                    top = module.split(".")[0]
                    if not top or top in stdlib() or top in local:
                        continue
                    acceptable = packageOf().get(top, frozenset((normalize(top),)))
                    if acceptable.isdisjoint(packages):
                        package = "`, `".join(sorted(acceptable))
                        yield Finding(
                            "installImport",
                            line,
                            code.strip(),
                            f"`{top}` 를 import 하는데 설치 줄에 허용되는 이름 `{package}` 가 없다. "
                            "독자는 ModuleNotFoundError 에서 멈춘다",
                            None,
                            "error",
                            DOCUMENT,
                            block.index,
                        )
            for pattern, requirement, why in hiddenDeps():
                if not pattern.search(code):
                    continue
                parsed = REQUIREMENT.match(requirement)
                if not parsed:
                    continue
                name = normalize(parsed.group(1))
                extra = normalize(parsed.group(2)) if parsed.group(2) else None
                if name in packages and (extra is None or extra in packages[name]):
                    continue
                yield Finding(
                    "installImport",
                    line,
                    code.strip(),
                    f"이 줄은 `{requirement}` 가 있어야 돈다. {why}. 설치 줄에 없다",
                    None,
                    NOTICE,
                    DOCUMENT,
                    block.index,
                )
