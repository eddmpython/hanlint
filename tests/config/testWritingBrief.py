import json
from pathlib import Path

import pytest

from hanlint import WritingBrief, loadWritingBrief
from hanlint.config import PRESET_NAMES, numberValues

ROOT = Path(__file__).resolve().parents[2]


def mapping(preset: str = "report") -> dict:
    return {
        "version": 1,
        "preset": preset,
        "reader": "결정할 운영자",
        "task": "관찰값을 읽고 다음 조치를 고른다",
        "facts": [
            {"id": "F1", "statement": "해솔 계획은 2026년 8월 31일 시작한다."},
            {"id": "F2", "statement": "예산은 380,000원이다."},
            {"id": "F3", "statement": "명세는 https://example.invalid/check 에 있다."},
            {"id": "F4", "statement": "확인 명령은 `mora check`다."},
        ],
        "mustInclude": ["해솔 계획", "380,000원", "https://example.invalid/check", "`mora check`"],
        "allowedNumbers": ["2026", "8", "31", "380000"],
        "forbidden": ["효과가 입증됐다"],
        "length": {"min": 100, "max": 500},
    }


@pytest.mark.parametrize("preset", PRESET_NAMES)
def testEveryPresetLoadsAsTheSameVersionedContract(preset: str):
    brief = WritingBrief.fromMapping(mapping(preset))
    assert brief.version == 1 and brief.preset == preset
    assert brief.allowedNumbers == ("2026", "31", "380000", "8")
    assert len(brief.digest) == 64 and brief.asDict()["facts"][0]["id"] == "F1"


def testLoadsUtf8JsonAndDigestDoesNotDependOnObjectKeyOrder(tmp_path):
    data = mapping()
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    loaded = loadWritingBrief(path)
    reordered = {key: data[key] for key in reversed(data)}
    assert loaded.digest == WritingBrief.fromMapping(reordered).digest
    assert loaded.asDict()["allowedNumbers"] == ["2026", "31", "380000", "8"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: data.update(version=3), "version"),
        (lambda data: data.update(version=1.0), "version"),
        (lambda data: data.update(extra=True), "모르는 키"),
        (lambda data: data["facts"].append({"id": "F1", "statement": "다른 사실이다."}), "id 가 겹친다"),
        (lambda data: data.update(mustInclude=["없는 표면"]), "reader, task, facts 안에"),
        (lambda data: data.update(allowedNumbers=["2026"]), "reader, task, facts 의 숫자 표면"),
        (lambda data: data.update(allowedNumbers=["380,000"]), "숫자와 소수점"),
        (lambda data: data.update(length={"min": 10, "max": 1}), "1 <= min <= max"),
    ],
)
def testRejectsAmbiguousOrIncompleteContracts(change, message):
    data = mapping()
    change(data)
    with pytest.raises(ValueError, match=message):
        WritingBrief.fromMapping(data)


def testNumberValuesNormalizeGroupingButKeepDecimalsAndIdentifiers():
    assert numberValues("380,000원, mora 1.4, R2와 A-17") == ("1.4", "17", "2", "380000")


def testNumberValuesDoNotMistakeACommaSeparatedListForThousands():
    assert numberValues("항목 1,2와 값 1,000,000 및 12,345.67") == ("1", "1000000", "12345.67", "2")


def testNumberValuesCanonicalizeUnicodeDecimalDigits():
    assert numberValues("전각 ２와 아라비아 문자 ٣") == ("2", "3")


def testTaskNumbersArePartOfTheAllowedOutputContract():
    data = mapping()
    data["task"] = "2주 뒤의 조치를 고른다"
    data["allowedNumbers"].append("2")
    brief = WritingBrief.fromMapping(data)
    assert "2" in brief.allowedNumbers


def testPublishedSchemaNamesTheSameClosedSurface():
    schema = json.loads((ROOT / "src" / "hanlint" / "data" / "writingBrief.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["version"]["const"] == 1
    assert tuple(schema["properties"]["preset"]["enum"]) == PRESET_NAMES
    assert set(schema["required"]) == set(mapping())
