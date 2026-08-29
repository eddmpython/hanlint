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
CATEGORIES = ("sentence", "paragraph", "structure", "document", "orthography", "code")
CATEGORY_TITLES = {
    "sentence": "문장 안에서 세는 것",
    "paragraph": "문단 사이에서 세는 것",
    "structure": "글의 짜임에서 세는 것",
    "document": "두 자리를 대조해 세는 것",
    "orthography": "표기와 띄어쓰기",
    "code": "코드 블록 사이를 대조하는 것",
}
"""부류의 사람 이름. `hanlint rules` 가 이 순서로 묶어 보인다. 뜻의 정본은 start.product 의 잡는 것이다."""
MECHANISMS = {
    "dictionary": "사전. 낱말 목록과 정규식이 맞는 자리",
    "repeat": "반복. 같은 모양이 창 안에서 N 번",
    "threshold": "셈. 지문의 값이 임계를 넘거나 모양이 계약과 다른 자리",
    "contrast": "대조. 두 자리를 맞대 어긋난 곳",
    "reader": "독자 상태. 문장 순서대로 독자가 손에 든 것과 본 것에 그 자리가 요구하는 것을 맞댄다",
}
"""규칙이 세는 방법의 닫힌 집합. 규칙은 쌓여도 기제는 늘지 않는다. 등록 시점에 이 밖의 기제를 거부하므로
여섯째 기제는 규칙 하나 때문에 조용히 들어오지 못한다. 새 기제가 정말 필요하면 여기를 고치기 전에 운영자에게
묻는다. 규칙과 기제의 대응은 `hanlint rules --format json` 과 npm 투영 `ruleMechanisms.json` 이 든다."""
MECHANISM_OF: dict[str, str] = {}


def rule(name: str, mechanism: str) -> Callable[[Check], Check]:
    if mechanism not in MECHANISMS:
        raise ValueError(
            f"규칙 {name} 의 기제 {mechanism} 은 닫힌 집합 밖이다 ({', '.join(MECHANISMS)}). "
            "새 기제는 규칙 하나 때문에 들어오지 않는다. 멈춰서 묻는다"
        )

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
        MECHANISM_OF[name] = mechanism
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


def ruleCategory(name: str) -> str:
    """규칙이 사는 부류 폴더 이름. 파일 위치가 정본이라 따로 적지 않는다."""
    loadAll()
    if name not in REGISTRY:
        raise KeyError(f"모르는 규칙: {name}. hanlint rules 로 목록을 본다")
    return REGISTRY[name].__module__.split(".")[-2]


def ruleCategories() -> dict[str, str]:
    """규칙 이름 → 부류. npm 투영 (`scripts/exportData.py`) 이 이것을 그대로 쓴다."""
    return {name: ruleCategory(name) for name in ruleNames()}


def ruleMechanism(name: str) -> str:
    """규칙이 세는 방법. MECHANISMS 의 키 하나."""
    loadAll()
    if name not in MECHANISM_OF:
        raise KeyError(f"모르는 규칙: {name}. hanlint rules 로 목록을 본다")
    return MECHANISM_OF[name]


def ruleMechanisms() -> dict[str, str]:
    """규칙 이름 → 기제. npm 투영 (`scripts/exportData.py`) 이 이것을 그대로 쓴다."""
    return {name: ruleMechanism(name) for name in ruleNames()}


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
