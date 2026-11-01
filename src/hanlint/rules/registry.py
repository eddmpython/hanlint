"""규칙 목록.

규칙 하나는 함수 하나다. `@rule("이름")`으로 등록한다. 등록 시점에 셋을 거부한다. 이름이 함수 이름과
다른 것, docstring이 없는 것, docstring에 네 절 (왜, 어디서, 고치기, 안 잡는 것)이 없는 것. 규칙의
docstring은 규칙 설명이라 `hanlint explain`이 그대로 보여 주고 네 절이 빠지면 설명이 되지 않는다.

규칙 모듈은 `loadAll`이 묶음 폴더를 돌며 전부 import 한다. 규칙 파일이 서로를 import 하지 않아도 되는
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
CATEGORIES = ("sentence", "paragraph", "structure", "document", "orthography", "code", "screen")
CATEGORY_TITLES = {
    "sentence": "문장",
    "paragraph": "문단",
    "structure": "글의 짜임",
    "document": "앞뒤 맞추기",
    "orthography": "표기와 띄어쓰기",
    "code": "코드 블록",
    "screen": "화면의 글",
}
"""규칙 묶음의 이름. `hanlint rules`가 이 순서로 묶어 보인다."""
MECHANISMS = {
    "dictionary": "사전. 단어 목록과 정규식이 맞는 곳",
    "repeat": "반복. 같은 모양이 가까이에서 여러 번 나오는 곳",
    "threshold": "수치. 글에서 잰 값이 기준값을 넘거나 정해 둔 형식과 다른 곳",
    "contrast": "비교. 두 곳을 비교해 어긋난 곳",
    "reader": "독자. 앞에서 읽은 내용만으로 그 문장을 이해할 수 있는지 문장 순서대로 본다",
}
"""규칙이 찾는 방법의 닫힌 목록. 규칙은 늘어도 찾는 방법은 늘지 않는다. 등록할 때 이 밖의 방법을 거부하므로
여섯째 방법이 규칙 하나 때문에 조용히 들어오지 못한다. 새 방법이 정말 필요하면 여기를 고치기 전에 운영자에게
묻는다. 규칙과 찾는 방법의 짝은 `hanlint rules --format json`과 npm 자료 `ruleMechanisms.json`에 있다."""
MECHANISM_OF: dict[str, str] = {}


def rule(name: str, mechanism: str) -> Callable[[Check], Check]:
    if mechanism not in MECHANISMS:
        raise ValueError(
            f"규칙 {name}의 찾는 방법이 닫힌 집합 밖이다: {mechanism} (있는 것: {', '.join(MECHANISMS)}). "
            "새 방법은 규칙 하나 때문에 더하지 않는다. 멈추고 묻는다"
        )

    def register(check: Check) -> Check:
        if check.__name__ != name:
            raise ValueError(f"규칙 이름과 함수 이름이 다르다: {name}, {check.__name__}. 셋(파일, 함수, id)이 같아야 한다")
        doc = inspect.getdoc(check) or ""
        missing = [section for section in REQUIRED_SECTIONS if section not in doc]
        if not doc or missing:
            raise ValueError(
                f"규칙 {name}의 docstring에 없는 절: {', '.join(missing) or '내용 전부'}. "
                "규칙 설명(기술서)이 되려면 네 절이 다 있어야 한다"
            )
        if name in REGISTRY and REGISTRY[name] is not check:
            raise ValueError(f"규칙 이름이 겹친다: {name}")
        REGISTRY[name] = check
        MECHANISM_OF[name] = mechanism
        return check

    return register


_loaded = False


def loadAll() -> None:
    """규칙 모듈을 전부 import 한다. 한 번 걸은 뒤에는 되돌아온다.

    실측: 글 마디 2,189개를 검사하는 `hanlint sheet`가 15.8초 가운데 11.4초를 `runAll`마다 폴더를 다시 걷는
    이 함수에 썼다 (2026-09-17). import는 파이썬이 캐시하지만 `pkgutil.iter_modules`는 매번 디스크를 읽는다.
    """
    global _loaded
    if _loaded:
        return
    package = importlib.import_module("hanlint.rules")
    for category in CATEGORIES:
        module = importlib.import_module(f"hanlint.rules.{category}")
        for info in pkgutil.iter_modules(module.__path__, f"{module.__name__}."):
            importlib.import_module(info.name)
    del package
    _loaded = True


def ruleNames() -> list[str]:
    loadAll()
    return sorted(REGISTRY)


def ruleCategory(name: str) -> str:
    """규칙이 사는 묶음 폴더 이름. 파일 위치가 정본이라 따로 적지 않는다."""
    loadAll()
    if name not in REGISTRY:
        raise KeyError(f"모르는 규칙: {name}. hanlint rules로 목록을 본다")
    return REGISTRY[name].__module__.split(".")[-2]


def ruleCategories() -> dict[str, str]:
    """규칙 이름 → 묶음. npm 투영 (`scripts/derive/npmData.py`)이 이것을 그대로 쓴다."""
    return {name: ruleCategory(name) for name in ruleNames()}


def ruleMechanism(name: str) -> str:
    """규칙이 세는 방법. MECHANISMS의 키 하나."""
    loadAll()
    if name not in MECHANISM_OF:
        raise KeyError(f"모르는 규칙: {name}. hanlint rules로 목록을 본다")
    return MECHANISM_OF[name]


def ruleMechanisms() -> dict[str, str]:
    """규칙 이름 → 기제. npm 투영 (`scripts/derive/npmData.py`)이 이것을 그대로 쓴다."""
    return {name: ruleMechanism(name) for name in ruleNames()}


def ruleDoc(name: str) -> str:
    loadAll()
    if name not in REGISTRY:
        raise KeyError(f"모르는 규칙: {name}. hanlint rules로 목록을 본다")
    return inspect.getdoc(REGISTRY[name]) or ""


def docSection(doc: str, label: str) -> str:
    """기술서에서 절 하나의 본문을 한 줄로. `고치기:`처럼 표를 주면 그 줄부터 다음 절 표나 빈 줄 앞까지를 잇는다."""
    collected: list[str] = []
    inside = False
    for raw in doc.splitlines():
        line = raw.strip()
        if not inside:
            if line.startswith(label):
                inside = True
                collected.append(line[len(label) :].strip())
            continue
        if not line or any(line.startswith(other) for other in REQUIRED_SECTIONS):
            break
        collected.append(line)
    return " ".join(part for part in collected if part)


def ruleFix(name: str) -> str:
    """규칙의 고치기 절 한 줄. primer가 쓰기 전에 읽히는 그 문장이다."""
    return docSection(ruleDoc(name), "고치기:")


def ruleSummary(name: str) -> str:
    return ruleDoc(name).splitlines()[0]


def isDisabledAt(finding: Finding, disabled: tuple[tuple[str, int, int], ...]) -> bool:
    """인라인 제어가 그 줄에서 그 규칙을 껐는가. `*`는 전부다."""
    return any((name == "*" or name == finding.rule) and start <= finding.line <= end for name, start, end in disabled)


def runAll(doc: DocumentPrint, config: Config) -> list[Finding]:
    loadAll()
    findings: list[Finding] = []
    for name in sorted(REGISTRY):
        if config.enabled(name):
            findings.extend(f for f in REGISTRY[name](doc, config) if not isDisabledAt(f, doc.disabled))
    findings.sort(key=lambda f: (f.line, f.rule))
    return findings
