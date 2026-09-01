import json
from pathlib import Path

import pytest

from hanlint.config import (
    CONTRACT_VERSION,
    LATEST_CONTRACT_VERSION,
    Contract,
    ContractV2,
    Outline,
    ProtectedSurface,
    loadContract,
    parseContract,
)

ROOT = Path(__file__).resolve().parents[2]


def mapping() -> dict:
    return {
        "version": 1,
        "reader": "배포를 결정할 운영자",
        "goal": "관찰값을 읽고 다음 조치를 고른다",
        "facts": [
            "해솔 계획은 2026년 8월 31일 시작한다.",
            "예산은 380,000원이다.",
            "명세는 https://example.invalid/check 에 있다.",
            "확인 명령은 `mora check`다.",
        ],
    }


def testLoadsClosedContractAndKeepsDeterministicDigest(tmp_path):
    data = mapping()
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    loaded = loadContract(path)
    reordered = {key: data[key] for key in reversed(data)}
    assert loaded == Contract.fromMapping(data)
    assert loaded.digest == Contract.fromMapping(reordered).digest
    assert loaded.text.endswith("확인 명령은 `mora check`다.")
    assert len(loaded.digest) == 64


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: data.update(version=2), "version"),
        (lambda data: data.update(version=True), "version"),
        (lambda data: data.update(extra=True), "모르는 키"),
        (lambda data: data.pop("goal"), "빠진 키"),
        (lambda data: data.update(facts=[]), "비지 않은 문자열 배열"),
        (lambda data: data.update(facts=["같다", "같다"]), "같은 값"),
        (lambda data: data.update(reader=" 양끝 공백"), "양끝 공백"),
        (lambda data: data.update(goal="글"), "NFC"),
    ],
)
def testRejectsOpenOrAmbiguousContracts(change, message):
    data = mapping()
    change(data)
    with pytest.raises(ValueError, match=message):
        Contract.fromMapping(data)


def testPublishedSchemaNamesTheSameClosedSurface():
    schema = json.loads((ROOT / "src" / "hanlint" / "data" / "readerContract.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["version"]["const"] == CONTRACT_VERSION
    assert set(schema["required"]) == set(mapping())
    assert schema["additionalProperties"] is False


def testLoadsVersionTwoWithSeparatedSurfaceAndOutline(tmp_path):
    data = {
        "version": 2,
        "reader": "데이터 도구를 고르는 개발자",
        "goal": "용도별 라이브러리를 비교한다",
        "facts": [],
        "surface": {
            "numbers": ["12"],
            "urls": ["https://example.invalid/data"],
            "code": ["import polars"],
            "links": [],
        },
        "outline": {"level": 2, "headings": ["pandas", "Polars"]},
    }
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    loaded = loadContract(path)
    assert loaded == ContractV2(
        reader=data["reader"],
        goal=data["goal"],
        facts=(),
        surface=ProtectedSurface(numbers=("12",), urls=("https://example.invalid/data",), code=("import polars",)),
        outline=Outline(2, ("pandas", "Polars")),
    )
    assert loaded.version == LATEST_CONTRACT_VERSION
    assert parseContract(data).digest == loaded.digest


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: data["surface"].update(extra=[]), "모르는 키"),
        (lambda data: data["outline"].update(level=7), "1~6"),
        (lambda data: data["outline"].update(headings=[]), "비지 않은 문자열 배열"),
    ],
)
def testRejectsAmbiguousVersionTwoContracts(change, message):
    data = {
        "version": 2,
        "reader": "독자",
        "goal": "목표",
        "facts": [],
        "surface": {"numbers": [], "urls": [], "code": [], "links": []},
        "outline": {"level": 2, "headings": ["첫 절"]},
    }
    change(data)
    with pytest.raises(ValueError, match=message):
        parseContract(data)
