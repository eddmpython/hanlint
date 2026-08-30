"""배포 함의 평가판에서 gold 누출, 중복, 출처·라이선스와 해시 변조를 막는다."""

import tomllib
from copy import deepcopy
from pathlib import Path

import pytest
from scripts.exportData import render

from hanlint.entailment import (
    BENCHMARK_ID,
    BENCHMARK_SHA256,
    SOURCE_REVISION,
    SOURCE_SHA256,
    checkedBenchmark,
    entailmentCases,
    shippedBenchmark,
)
from scripts import buildEntailmentBenchmark

ROOT = Path(__file__).resolve().parents[2]


def testEntailmentDataBoundaryIsClosed():
    benchmark = checkedBenchmark(shippedBenchmark())
    public = entailmentCases()
    assert len(benchmark["cases"]) == len(public["cases"]) == 36
    assert benchmark["source"]["license"] == "CC-BY-SA-4.0"
    assert benchmark["selection"]["premiseDuplicates"] == benchmark["selection"]["hypothesisDuplicates"] == 0
    assert all(set(case) == {"caseId", "domain", "evidenceExcerpt", "atomicFact"} for case in public["cases"])


def testEntailmentBuilderProjectionAndPackageLicenseStayPinned():
    benchmark = shippedBenchmark()
    assert benchmark["benchmarkId"] == BENCHMARK_ID and benchmark["contentSha256"] == BENCHMARK_SHA256
    assert buildEntailmentBenchmark.SOURCE_REVISION == SOURCE_REVISION
    assert buildEntailmentBenchmark.SOURCE_SHA256 == SOURCE_SHA256
    projected = render()
    assert "evidenceEntailmentV1.json" not in projected
    assert "entailmentPredictions.schema.json" in projected and "evidenceEntailmentBenchmark.schema.json" in projected
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "src/hanlint/data/evidenceEntailmentV1.LICENSE.md" in project["project"]["license-files"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: data["cases"][0].update(evidenceExcerpt="변조"), "문장 SHA256"),
        (
            lambda data: data["cases"][1].update(
                evidenceExcerpt=data["cases"][0]["evidenceExcerpt"],
                excerptSha256=data["cases"][0]["excerptSha256"],
            ),
            "전제나 가설이 겹친다",
        ),
        (lambda data: data["cases"][0].update(license="MIT"), "라이선스"),
        (lambda data: data["source"].update(license="MIT"), "고정 KLUE-NLI 판"),
        (lambda data: data["cases"][0].update(caseSha256="0" * 64), "caseSha256"),
        (lambda data: data.update(contentSha256="0" * 64), "contentSha256"),
    ],
)
def testEntailmentDataGateHasTeeth(change, message):
    data = deepcopy(shippedBenchmark())
    change(data)
    with pytest.raises(ValueError, match=message):
        checkedBenchmark(data)
