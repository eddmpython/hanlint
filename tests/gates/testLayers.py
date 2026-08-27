"""층 구조 게이트. import 가 아래로만 가는지, 형제와 규칙끼리 교차하지 않는지 본다.

판정은 순수 함수 `layerViolations(files)` 이고 실제 소스 트리와 합성 fixture 양쪽에 돌린다.
소스가 아직 없으면 실제 트리 검사는 건너뛴다고 말하고 fixture 검사만으로 이빨을 증명한다.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from tests.gates.layerContract import LAYERS, PACKAGE, RULE_LAYER, RULE_SHARED

SRC = Path(__file__).resolve().parents[2] / "src" / PACKAGE


def layerOf(modulePath: str) -> str | None:
    """`hanlint/rules/sentence/deixis.py` 같은 패키지 상대 경로의 층 이름."""
    parts = modulePath.split("/")
    if len(parts) < 2:
        return None
    return parts[1] if parts[1] in LAYERS else None


def importedModules(source: str, modulePath: str) -> list[str]:
    """소스가 import 하는 패키지 내부 모듈을 패키지 상대 경로로 돌려준다."""
    tree = ast.parse(source)
    parts = modulePath.split("/")
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = parts[: len(parts) - node.level]
                target = base + (node.module.split(".") if node.module else [])
                imported.append("/".join(target))
            elif node.module and node.module.split(".")[0] == PACKAGE:
                imported.append(node.module.replace(".", "/"))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == PACKAGE:
                    imported.append(alias.name.replace(".", "/"))
    return imported


def layerViolations(files: dict[str, str]) -> list[str]:
    """{패키지 상대 경로: 소스} 를 받아 위반 설명 목록을 준다."""
    violations: list[str] = []
    for modulePath, source in files.items():
        if not modulePath.endswith(".py"):
            continue
        fromLayer = layerOf(modulePath)
        for target in importedModules(source, modulePath):
            toLayer = layerOf(target + ".py") or layerOf(target + "/x.py")
            if fromLayer is None or toLayer is None:
                continue
            if LAYERS[toLayer] > LAYERS[fromLayer]:
                violations.append(f"{modulePath} 가 위층 {toLayer} 를 import 한다")
            elif LAYERS[toLayer] == LAYERS[fromLayer] and toLayer != fromLayer:
                violations.append(f"{modulePath} 가 형제 층 {toLayer} 를 import 한다")
            elif fromLayer == RULE_LAYER and toLayer == RULE_LAYER:
                targetParts = target.split("/")
                if (
                    len(targetParts) > 2
                    and targetParts[2] != RULE_SHARED
                    and not targetParts[2].endswith("registry")
                ):
                    violations.append(
                        f"{modulePath} 가 다른 규칙 {target} 를 import 한다. 공통은 rules/shared 에 둔다"
                    )
    return violations


def realTree() -> dict[str, str]:
    if not SRC.exists():
        return {}
    return {
        f"{PACKAGE}/{path.relative_to(SRC).as_posix()}": path.read_text(encoding="utf-8")
        for path in SRC.rglob("*.py")
    }


def testRealTreeHasNoLayerViolations():
    files = realTree()
    if not files:
        pytest.skip("src/hanlint 가 아직 없다. fixture 검사가 이빨을 증명한다")
    assert layerViolations(files) == []


def testSparesDownwardImports():
    files = {
        f"{PACKAGE}/rules/sentence/deixis.py": (
            "from ...fingerprint.sentencePrint import SentencePrint\n"
            "from ..registry import rule\n"
            "from ..shared.lineOf import lineOf\n"
        ),
        f"{PACKAGE}/report/textReport.py": (
            "from ..rules.finding import Finding\nfrom ..audit.shape import Shape\n"
        ),
        f"{PACKAGE}/cli/main.py": "from hanlint.report.textReport import render\n",
        f"{PACKAGE}/document/parseMarkdown.py": "import re\nfrom ..config.settings import Config\n",
    }
    assert layerViolations(files) == []


def testCatchesUpwardImport():
    files = {f"{PACKAGE}/document/parseMarkdown.py": "from ..rules.finding import Finding\n"}
    assert layerViolations(files) == ["hanlint/document/parseMarkdown.py 가 위층 rules 를 import 한다"]


def testCatchesSiblingImport():
    files = {f"{PACKAGE}/audit/shape.py": "from ..rules.registry import runAll\n"}
    assert layerViolations(files) == ["hanlint/audit/shape.py 가 형제 층 rules 를 import 한다"]


def testCatchesRuleImportingRule():
    files = {f"{PACKAGE}/rules/sentence/deixis.py": "from .cliche import cliche\n"}
    assert len(layerViolations(files)) == 1
    assert "다른 규칙" in layerViolations(files)[0]


def testSparesRuleImportingSharedAndRegistry():
    files = {
        f"{PACKAGE}/rules/sentence/deixis.py": (
            "from ..shared.proseSentences import proseSentences\nfrom ..registry import rule\n"
        )
    }
    assert layerViolations(files) == []


def testAbsoluteImportIsCheckedToo():
    files = {f"{PACKAGE}/analysis/analyzer.py": "import hanlint.fingerprint.build\n"}
    assert layerViolations(files) == ["hanlint/analysis/analyzer.py 가 위층 fingerprint 를 import 한다"]


def testIgnoresStandardLibraryAndUnknown():
    files = {f"{PACKAGE}/cli/main.py": "import re\nimport json\nfrom pathlib import Path\n"}
    assert layerViolations(files) == []
    assert re.match(r"\w", "x")
