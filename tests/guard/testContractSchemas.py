import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "hanlint" / "data"


def read(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def testPublishedSchemasCoverTheThreePublicConceptsAndReceipts():
    contract = read("readerContract.schema.json")
    finding = read("finding.schema.json")
    patch = read("patch.schema.json")
    assert set(contract["required"]) == {"version", "reader", "goal", "facts"}
    assert set(finding["required"]) == {"rule", "line", "severity", "scope", "at", "quote", "why"}
    assert set(patch["required"]) == {"reason", "before", "after"}
    assert all(schema["additionalProperties"] is False for schema in (contract, finding, patch))


def testReceiptSchemasNameEveryPublishedTopLevelField():
    suite = read("readerContractConformanceV1.json")
    checkSchema = read("checkResult.schema.json")
    patchSchema = read("patchResult.schema.json")
    assert set(checkSchema["required"]) == set(suite["checks"][0]["expected"])
    assert set(patchSchema["required"]) == set(suite["patches"][0]["expected"])
    assert checkSchema["properties"]["kind"]["const"] == "hanlint.checkResult"
    assert patchSchema["properties"]["kind"]["const"] == "hanlint.patchResult"
