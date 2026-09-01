import json
from pathlib import Path

from hanlint import Config, Contract, Patch, check, ruleNames, verifyPatch

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "src" / "hanlint" / "data" / "readerContractConformanceV1.json"


def testPythonMatchesThePublishedSurfaceConformanceSuite():
    suite = json.loads(SUITE.read_text(encoding="utf-8"))
    contract = Contract.fromMapping(suite["contract"])
    config = Config(disable=set(ruleNames()))
    assert suite["mode"] == "surfaceOnly"
    assert contract.digest == suite["contractSha256"]
    for case in suite["checks"]:
        assert check(case["text"], contract, config).asDict() == case["expected"], case["id"]
    for case in suite["patches"]:
        patch = Patch.fromMapping(case["patch"])
        assert verifyPatch(case["text"], patch, contract, config).asDict() == case["expected"], case["id"]
