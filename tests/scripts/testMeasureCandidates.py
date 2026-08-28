from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "measureCandidates.py"


def loadScript():
    spec = importlib.util.spec_from_file_location("measureCandidates", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def testEvenlyKeepsEdgesAndLimit():
    module = loadScript()
    items = [{"id": str(index)} for index in range(30)]
    selected = module.evenly(items, 10)
    assert len(selected) == 10
    assert selected[0] == items[0]
    assert selected[-1] == items[-1]


def testCandidateIdIsStable():
    module = loadScript()
    assert module.observationId("doc", "rule", 3, "quote") == module.observationId("doc", "rule", 3, "quote")
    assert module.observationId("doc", "rule", 3, "quote") != module.observationId("doc", "rule", 4, "quote")
