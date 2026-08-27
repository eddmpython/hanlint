"""규칙 등록부.

규칙 하나는 함수 하나다. `@rule("이름")` 으로 등록한다. 등록 시점에 셋을 거부한다. 이름이 함수 이름과
다른 것, docstring 이 없는 것, docstring 에 네 절 (왜, 어디서, 고치기, 안 잡는 것) 이 없는 것. 규칙의
docstring 은 기술서라 `hanlint explain` 이 그대로 보여 주고 네 절이 빠지면 기술서가 아니다.

규칙 모듈은 `loadAll` 이 부류 폴더를 걸어 전부 import 한다. 규칙 파일이 서로를 import 하지 않아도 되는
이유가 이것이다.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections.abc import Callable, Iterable

from ..config import Config
from ..fingerprint import DocumentPrint
from .finding import Finding

Check = Callable[[DocumentPrint, Config], Iterable[Finding]]
REGISTRY: dict[str, Check] = {}
REQUIRED_SECTIONS = ("왜:", "어디서:", "고치기:", "안 잡는 것:")
CATEGORIES = ("sentence", "paragraph", "structure", "document")


def rule(name: str) -> Callable[[Check], Check]:
    def register(check: Check) -> Check:
        if check.__name__ != name:
            raise ValueError(f"규칙 이름 {name} 과 함수 이름 {check.__name__} 이 다르다. 셋 (파일, 함수, id) 이 같아야 한다")
        doc = inspect.getdoc(check) or ""
        missing = [section for section in REQUIRED_SECTIONS if section not in doc]
        if not doc or missing:
            raise ValueError(f"규칙 {name} 의 docstring 에 {', '.join(missing) or '내용'} 이 없다. 기술서가 아니다")
        if name in REGISTRY and REGISTRY[name] is not check:
            raise ValueError(f"규칙 이름이 겹친다: {name}")
        REGISTRY[name] = check
        return check

    return register


def loadAll() -> None:
    package = importlib.import_module("hanlint.rules")
    for category in CATEGORIES:
        module = importlib.import_module(f"hanlint.rules.{category}")
        for info in pkgutil.iter_modules(module.__path__, f"{module.__name__}."):
            importlib.import_module(info.name)
    del package


def ruleNames() -> list[str]:
    loadAll()
    return sorted(REGISTRY)


def ruleDoc(name: str) -> str:
    loadAll()
    if name not in REGISTRY:
        raise KeyError(f"모르는 규칙: {name}. hanlint rules 로 목록을 본다")
    return inspect.getdoc(REGISTRY[name]) or ""


def ruleSummary(name: str) -> str:
    return ruleDoc(name).splitlines()[0]


def isDisabledAt(finding: Finding, disabled: tuple[tuple[str, int, int], ...]) -> bool:
    """인라인 제어가 그 줄에서 그 규칙을 껐는가. `*` 는 전부다."""
    return any((name == "*" or name == finding.rule) and start <= finding.line <= end for name, start, end in disabled)


def runAll(doc: DocumentPrint, config: Config) -> list[Finding]:
    loadAll()
    findings: list[Finding] = []
    for name in sorted(REGISTRY):
        if config.enabled(name):
            findings.extend(f for f in REGISTRY[name](doc, config) if not isDisabledAt(f, doc.disabled))
    findings.sort(key=lambda f: (f.line, f.rule))
    return findings
