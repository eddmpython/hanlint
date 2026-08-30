"""근거 원장 v2가 정상 연결을 받고 누락·고아·변조·움직이는 판을 막는지 재현한다."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from tests.evidence.testEvidence import evidenceBrief  # noqa: E402

from hanlint import evidenceLedger  # noqa: E402


def stableDigest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode()).hexdigest()


def probe() -> dict:
    cases = {"valid": evidenceBrief()}
    missing = deepcopy(cases["valid"])
    missing["evidence"].pop()
    cases["missing"] = missing
    orphan = deepcopy(cases["valid"])
    orphan["evidence"][0]["factIds"] = ["F9"]
    cases["orphan"] = orphan
    tampered = deepcopy(cases["valid"])
    tampered["evidence"][0]["excerpt"] = "바뀐 근거 조각"
    cases["tampered"] = tampered
    moving = deepcopy(cases["valid"])
    moving["evidence"][0]["revision"] = "latest"
    cases["movingRevision"] = moving
    results = {name: evidenceLedger(data).asDict() for name, data in cases.items()}
    assert results["valid"]["ledgerValid"]
    assert all(not result["ledgerValid"] for name, result in results.items() if name != "valid")
    payload = {
        "version": 1,
        "cases": len(results),
        "valid": sum(result["ledgerValid"] for result in results.values()),
        "rejected": sum(not result["ledgerValid"] for result in results.values()),
        "violationKinds": {name: result["violations"] for name, result in results.items() if result["violations"]},
        "meaning": results["valid"]["meaning"],
    }
    payload["contentSha256"] = stableDigest(payload)
    return payload


if __name__ == "__main__":
    result = probe()
    print(json.dumps(result, ensure_ascii=False, indent=2))
