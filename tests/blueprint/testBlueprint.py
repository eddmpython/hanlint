import json
import tomllib
from copy import deepcopy
from pathlib import Path

import pytest

from hanlint import STRATEGY_ID, WritingBrief, blueprintFor, rhetoricalBlueprint
from hanlint.config import PRESET_NAMES
from hanlint.data.blueprints import blueprintBoundaryViolations, shippedBlueprints

ROOT = Path(__file__).resolve().parents[2]


def brief(preset: str) -> WritingBrief:
    return WritingBrief.fromMapping(
        {
            "version": 1,
            "preset": preset,
            "reader": "해솔 계획을 결정할 운영자",
            "task": "관찰값을 읽고 다음 확인 순서를 정한다",
            "facts": [{"id": "F1", "statement": "해솔 계획은 2026년 8월 31일 시작한다."}],
            "mustInclude": ["해솔 계획", "2026년 8월 31일"],
            "allowedNumbers": ["2026", "8", "31"],
            "forbidden": [],
            "length": {"min": 600, "max": 900},
        }
    )


@pytest.mark.parametrize("preset", PRESET_NAMES)
def testEveryPresetGetsAnExactBudgetWithoutFactMaterial(preset: str):
    result = rhetoricalBlueprint(brief(preset))
    assert result["strategyId"] == STRATEGY_ID and result["input"]["targetCharacters"] == 750
    roles = result["budget"]["roles"]
    assert [role["role"] for role in roles] == ["opening", "body", "closing"]
    assert roles[0]["startPermille"] == 0 and roles[-1]["endPermille"] == 1000
    assert all(left["endPermille"] == right["startPermille"] for left, right in zip(roles, roles[1:], strict=False))
    assert sum(role["characters"] for role in roles) == 750
    assert sum(role["paragraphs"] for role in roles) == result["budget"]["paragraphs"]
    assert sum(role["sentences"] for role in roles) == result["budget"]["sentences"]
    assert all(role["characters"] >= role["sentences"] >= role["paragraphs"] >= 1 for role in roles)
    sections = result["budget"]["sectionBudgets"]
    assert len(sections) == result["budget"]["sections"]
    assert sum(section["characters"] for section in sections) == 750
    assert sum(section["paragraphs"] for section in sections) == result["budget"]["paragraphs"]
    assert sum(section["sentences"] for section in sections) == result["budget"]["sentences"]
    assert all(section["sentences"] >= section["paragraphs"] >= 1 for section in sections)
    rendered = json.dumps(result, ensure_ascii=False)
    assert "해솔 계획" not in rendered and "2026년 8월 31일" not in rendered
    assert "품질 점수" in rendered and "정답" in rendered


def testShippedDataContainsOnlyClosedNumericStructureAndProvenance():
    raw = json.loads((ROOT / "src" / "hanlint" / "data" / "blueprints.json").read_text(encoding="utf-8"))
    corpus, references = shippedBlueprints()
    assert corpus["documents"] == 1600 and corpus["containsSourceText"] is False
    assert set(references) == {"blog", "technicalDocs", "report", "essay", "guide", "encyclopedia", "fiction"}
    assert blueprintBoundaryViolations(raw) == ()
    requiredMetrics = {
        "sections",
        "sectionParagraphs",
        "sectionSentences",
        "paragraphSentences",
        "sentenceCharacters",
        "adjacentSentenceCharacterDelta",
        "openingSharePermille",
        "closingSharePermille",
    }
    for reference in references.values():
        assert requiredMetrics <= set(reference.metrics)
        for metric in reference.metrics.values():
            assert 0 <= metric["p10"] <= metric["p25"] <= metric["p50"] <= metric["p75"] <= metric["p90"]
        assert reference.metrics["openingSharePermille"]["p90"] <= 1000
        assert reference.metrics["closingSharePermille"]["p90"] <= 1000


def testBlueprintBoundaryGateRejectsAHiddenSourceSentence():
    raw = json.loads((ROOT / "src" / "hanlint" / "data" / "blueprints.json").read_text(encoding="utf-8"))
    leaked = deepcopy(raw)
    leaked["types"]["blog"]["sourceText"] = "말뭉치에서 가져온 원문 문장이다."
    violations = blueprintBoundaryViolations(leaked)
    assert len(violations) == 1 and "출처 ID나 SHA256이 아닌 문자열" in violations[0]

    leaked = deepcopy(raw)
    leaked["types"]["blog"]["text"] = "kubernetesWebsite"
    violations = blueprintBoundaryViolations(leaked)
    assert len(violations) == 1 and "원문을 실을 수 있는 키" in violations[0]


def testEveryBlueprintSourceIdExistsInTheLicensedCatalogue():
    catalogue = tomllib.loads((ROOT / "corpus" / "catalogue.toml").read_text(encoding="utf-8"))
    sources = {source["id"]: source for source in catalogue["source"]}
    _, references = shippedBlueprints()
    used = {sourceId for reference in references.values() for sourceId in reference.sourceIds}
    assert used <= set(sources)
    for sourceId in used:
        assert sources[sourceId]["license"] and sources[sourceId]["licenseUrl"]


def testVeryShortBriefCollapsesToOneWholeBudget():
    data = brief("docs").asDict()
    data["length"] = {"min": 40, "max": 80}
    result = rhetoricalBlueprint(data)
    assert result["budget"]["sections"] == 1
    assert result["budget"]["roles"] == [
        {
            "role": "whole",
            "startPermille": 0,
            "endPermille": 1000,
            "characters": 60,
            "paragraphs": 1,
            "sentences": 1,
        }
    ]


def testUnknownStrategyIsNotSilentlyTreatedAsTheCurrentOne():
    with pytest.raises(ValueError, match="모르는 작법 전략"):
        blueprintFor(brief("docs"), "futureStrategy")


def testAConsumerCannotPoisonTheShippedBlueprintCache():
    corpus, references = shippedBlueprints()
    corpus["documents"] = 0
    references["blog"].metrics["sections"]["p50"] = 999
    freshCorpus, freshReferences = shippedBlueprints()
    assert freshCorpus["documents"] == 1600
    assert freshReferences["blog"].metrics["sections"]["p50"] == 5
