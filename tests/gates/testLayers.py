"""층 구조 게이트. import 가 아래로만 가는지, 형제와 규칙끼리 교차하지 않는지 본다.

판정은 순수 함수 `layerViolations(files)` 이고 실제 소스 트리와 합성 fixture 양쪽에 돌린다.
소스가 아직 없으면 실제 트리 검사는 건너뛴다고 말하고 fixture 검사만으로 이빨을 증명한다.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from tests.gates.layerContract import JS_ROOT, LAYERS, PACKAGE, RULE_LAYER, RULE_SHARED

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / PACKAGE
NPM_SRC = ROOT / "npm" / "src"
JS_IMPORT = re.compile(r"""^\s*import\s+(?:[^'"]*?\s+from\s+)?['"](\.[^'"]+)['"]""", re.MULTILINE)


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
                if node.module:
                    imported.append("/".join(base + node.module.split(".")))
                else:
                    # `from . import cliche` 는 형제 모듈을 이름으로 가져온다. 각 이름이 대상이다.
                    imported.extend("/".join(base + [alias.name]) for alias in node.names)
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
                # 규칙 파일은 깊이 4 (hanlint/rules/<부류>/<규칙>) 다. rules 최상위 모듈 (registry,
                # finding) 과 rules/shared 는 되고, 다른 부류 폴더 안의 파일은 안 된다.
                targetParts = target.split("/")
                if len(targetParts) > 3 and targetParts[2] != RULE_SHARED:
                    violations.append(f"{modulePath} 가 다른 규칙 {target} 를 import 한다. 공통은 rules/shared 에 둔다")
    return violations


def realTree() -> dict[str, str]:
    if not SRC.exists():
        return {}
    return {f"{PACKAGE}/{path.relative_to(SRC).as_posix()}": path.read_text(encoding="utf-8") for path in SRC.rglob("*.py")}


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
        f"{PACKAGE}/report/textReport.py": ("from ..rules.finding import Finding\nfrom ..audit.shape import Shape\n"),
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


def testCatchesRuleImportingSiblingByName():
    files = {f"{PACKAGE}/rules/sentence/deixis.py": "from . import cliche\n"}
    assert len(layerViolations(files)) == 1


def testSparesRuleImportingFindingAndRegistry():
    files = {f"{PACKAGE}/rules/structure/introLong.py": ("from ..finding import Finding\nfrom ..registry import rule\n")}
    assert layerViolations(files) == []


def testSparesRuleImportingSharedAndRegistry():
    files = {
        f"{PACKAGE}/rules/sentence/deixis.py": (
            "from ..shared.proseSentences import proseSentences\nfrom ..registry import rule\n"
        )
    }
    assert layerViolations(files) == []


def testAbsoluteImportIsCheckedToo():
    files = {f"{PACKAGE}/analysis/tokenize.py": "import hanlint.fingerprint.build\n"}
    assert layerViolations(files) == ["hanlint/analysis/tokenize.py 가 위층 fingerprint 를 import 한다"]


def testIgnoresStandardLibraryAndUnknown():
    files = {f"{PACKAGE}/cli/main.py": "import re\nimport json\nfrom pathlib import Path\n"}
    assert layerViolations(files) == []
    assert re.match(r"\w", "x")


# npm 은 같은 층을 거울처럼 따른다. 경로는 저장소 상대 (npm/src/rules/sentence/deixis.js).


def jsLayerOf(modulePath: str) -> str | None:
    """루트 도우미 (text.js, regex.js) 는 util 층, index.js 는 공개 표면이라 층이 아니다."""
    parts = modulePath.split("/")
    if parts[:2] != ["npm", "src"] or len(parts) < 3:
        return None
    if len(parts) == 3:
        return None if parts[2] == "index.js" else JS_ROOT
    return parts[2] if parts[2] in LAYERS else None


def normalizePath(path: str) -> str:
    parts: list[str] = []
    for part in path.split("/"):
        if part == "..":
            parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts)


def jsImportedModules(source: str, modulePath: str) -> list[str]:
    folder = modulePath.rsplit("/", 1)[0]
    return [normalizePath(f"{folder}/{target}") for target in JS_IMPORT.findall(source)]


def jsLayerViolations(files: dict[str, str]) -> list[str]:
    violations: list[str] = []
    for modulePath, source in files.items():
        fromLayer = jsLayerOf(modulePath)
        if fromLayer is None:
            continue
        isRuleFile = fromLayer == RULE_LAYER and len(modulePath.split("/")) > 4
        for target in jsImportedModules(source, modulePath):
            toLayer = jsLayerOf(target)
            if toLayer is None:
                continue
            if LAYERS[toLayer] > LAYERS[fromLayer]:
                violations.append(f"{modulePath} 가 위층 {toLayer} 를 import 한다")
            elif LAYERS[toLayer] == LAYERS[fromLayer] and toLayer != fromLayer:
                violations.append(f"{modulePath} 가 형제 층 {toLayer} 를 import 한다")
            elif isRuleFile and toLayer == RULE_LAYER:
                targetParts = target.split("/")
                if len(targetParts) > 4 and targetParts[3] != RULE_SHARED:
                    violations.append(f"{modulePath} 가 다른 규칙 {target} 를 import 한다. 공통은 rules/shared 에 둔다")
    return violations


def realJsTree() -> dict[str, str]:
    if not NPM_SRC.exists():
        return {}
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in NPM_SRC.rglob("*.js")
        if "node_modules" not in path.parts
    }


def testRealJsTreeHasNoLayerViolations():
    files = realJsTree()
    if not files:
        pytest.skip("npm/src 가 없다")
    assert jsLayerViolations(files) == []


def testJsSparesDownwardAndRegistry():
    files = {
        "npm/src/rules/sentence/deixis.js": (
            'import { overlap } from "../../fingerprint/topics.js";\nimport { finding } from "../finding.js";\n'
        ),
        "npm/src/rules/registry.js": (
            'import * as cliche from "./sentence/cliche.js";\nimport { enabled } from "../config/settings.js";\n'
        ),
        "npm/src/data/load.js": 'import { compile } from "../regex.js";\n',
        "npm/src/index.js": 'import { runAll } from "./rules/registry.js";\n',
        "npm/src/cli/main.js": 'import { readFileSync } from "node:fs";\nimport { lintText } from "../index.js";\n',
    }
    assert jsLayerViolations(files) == []


def testJsCatchesUpwardSiblingRuleAndUtility():
    assert jsLayerViolations({"npm/src/document/model.js": 'import { x } from "../rules/finding.js";\n'}) == [
        "npm/src/document/model.js 가 위층 rules 를 import 한다"
    ]
    assert jsLayerViolations({"npm/src/audit/shape.js": 'import { runAll } from "../rules/registry.js";\n'}) == [
        "npm/src/audit/shape.js 가 형제 층 rules 를 import 한다"
    ]
    assert "다른 규칙" in jsLayerViolations({"npm/src/rules/sentence/deixis.js": 'import { run } from "./cliche.js";\n'})[0]
    assert jsLayerViolations({"npm/src/text.js": 'import { loadLines } from "./data/load.js";\n'}) == [
        "npm/src/text.js 가 위층 data 를 import 한다"
    ]
