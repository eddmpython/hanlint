import json
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from hanlint import EntailmentPredictions, entailmentCases, evaluateEntailment
from hanlint.entailment import ENTAILMENT_MEANING, checkedBenchmark, shippedBenchmark, stableDigest

ROOT = Path(__file__).resolve().parents[2]


def oraclePredictions(label: str | None = None, confidence: float = 1.0) -> dict:
    benchmark = shippedBenchmark()
    return {
        "version": 1,
        "kind": "hanlint.entailmentPredictions",
        "benchmarkId": benchmark["benchmarkId"],
        "benchmarkSha256": benchmark["contentSha256"],
        "evaluator": {
            "id": "fixture-oracle",
            "kind": "rule",
            "revision": "fixture-v1",
            "promptSha256": "a" * 64,
        },
        "predictions": [
            {
                "caseId": case["id"],
                "label": label or case["goldLabel"],
                "confidence": 0 if label == "abstain" else confidence,
            }
            for case in benchmark["cases"]
        ],
    }


def testShippedBenchmarkPinsSourceConsensusBalanceLicenseAndHashes():
    benchmark = shippedBenchmark()
    assert benchmark["source"] == {
        "name": "KLUE-NLI v1.1 dev",
        "repositoryUrl": "https://github.com/KLUE-benchmark/KLUE",
        "paperUrl": "https://arxiv.org/html/2105.09680v4",
        "sourceUrl": "https://raw.githubusercontent.com/KLUE-benchmark/KLUE/3efd98708a40ff49251fddde35453f8fbb11f536/klue_benchmark/klue-nli-v1.1/klue-nli-v1.1_dev.json",
        "revision": "3efd98708a40ff49251fddde35453f8fbb11f536",
        "sourceSha256": "0699db82be17766b26e199864e6260443e17ec6e91d1870e876419e388f245b1",
        "license": "CC-BY-SA-4.0",
        "attribution": "KLUE Benchmark contributors",
    }
    assert len(benchmark["cases"]) == 36
    assert len({case["evidenceExcerpt"] for case in benchmark["cases"]}) == 36
    assert len({case["atomicFact"] for case in benchmark["cases"]}) == 36
    bins = {
        (domain, label): sum(case["domain"] == domain and case["goldLabel"] == label for case in benchmark["cases"])
        for domain in benchmark["selection"]["sources"]
        for label in ("supported", "contradicted", "insufficient")
    }
    assert set(bins.values()) == {2}
    for case in benchmark["cases"]:
        assert case["annotation"]["agreeingVotes"] >= 4 and case["annotation"]["totalVotes"] == 5
        assert case["excerptSha256"] == sha256(case["evidenceExcerpt"].encode()).hexdigest()
        assert case["factSha256"] == sha256(case["atomicFact"].encode()).hexdigest()
        assert case["caseSha256"] == stableDigest({key: value for key, value in case.items() if key != "caseSha256"})
        assert case["license"] == "CC-BY-SA-4.0"
    assert benchmark["contentSha256"] == "864e8af5bb88e16521e630c9f8987b32b36916c1042fee6a8ee54e76d7d8f5d8"
    licenseText = (ROOT / "src" / "hanlint" / "data" / "evidenceEntailmentV1.LICENSE.md").read_text(encoding="utf-8")
    assert "CC BY-SA 4.0" in licenseText and benchmark["source"]["revision"] in licenseText


def testPublicCasesHideGoldVotesAndSourceIdentifiers():
    public = entailmentCases()
    assert public["benchmarkSha256"] == shippedBenchmark()["contentSha256"]
    assert len(public["cases"]) == 36
    assert set(public["cases"][0]) == {"caseId", "domain", "evidenceExcerpt", "atomicFact"}
    encoded = json.dumps(public, ensure_ascii=False)
    assert "goldLabel" not in encoded and "validatorLabels" not in encoded and "sourceGuid" not in encoded
    assert "문장 자체가 세상에서 참인지는 묻지 않는다" in public["meaning"]


def testOracleMetricsAreExactAndInputOrderDoesNotMatter():
    data = oraclePredictions()
    result = evaluateEntailment(data).asDict()
    metrics = result["metrics"]
    assert metrics["totalCases"] == metrics["answered"] == 36 and metrics["abstained"] == 0
    assert metrics["coverage"] == 1.0
    assert metrics["selectedAccuracy"] == {"correct": 36, "answered": 36, "ratio": 1.0}
    assert metrics["selectiveRisk"] == {"errors": 0, "answered": 36, "ratio": 0.0}
    assert metrics["macroF1"] == 1.0 and all(item["f1"] == 1.0 for item in metrics["perClass"].values())
    assert metrics["riskCoverageCurve"] == [
        {"threshold": 1.0, "answered": 36, "errors": 0, "coverage": 1.0, "selectiveRisk": 0.0}
    ]
    assert result["meaning"] == ENTAILMENT_MEANING
    reordered = deepcopy(data)
    reordered["predictions"].reverse()
    assert evaluateEntailment(reordered).asDict() == result


def testAbstentionAndConfidenceProduceCoverageRiskCurveWithoutHidingErrors():
    data = oraclePredictions(confidence=0.5)
    data["predictions"][0].update(label="supported", confidence=1.0)
    data["predictions"][1].update(label="abstain", confidence=0)
    metrics = evaluateEntailment(data).metrics
    assert metrics["answered"] == 35 and metrics["abstained"] == 1 and metrics["coverage"] == 0.9722
    assert metrics["selectedAccuracy"] == {"correct": 34, "answered": 35, "ratio": 0.9714}
    assert metrics["selectiveRisk"] == {"errors": 1, "answered": 35, "ratio": 0.0286}
    assert metrics["macroF1"] == 0.9564
    assert metrics["riskCoverageCurve"] == [
        {"threshold": 1.0, "answered": 1, "errors": 1, "coverage": 0.0278, "selectiveRisk": 1.0},
        {"threshold": 0.5, "answered": 35, "errors": 1, "coverage": 0.9722, "selectiveRisk": 0.0286},
    ]


def testAllAbstainKeepsMacroF1AndCoverageVisible():
    result = evaluateEntailment(oraclePredictions("abstain")).asDict()
    metrics = result["metrics"]
    assert metrics["coverage"] == 0.0 and metrics["macroF1"] == 0.0
    assert metrics["selectedAccuracy"]["ratio"] is None and metrics["selectiveRisk"]["ratio"] is None
    assert metrics["riskCoverageCurve"] == []
    assert all(row["abstain"] == 12 for row in metrics["confusionMatrix"].values())


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: data.update(version=True), "version 또는 kind"),
        (lambda data: data.update(benchmarkSha256="0" * 64), "고정 benchmark 판"),
        (lambda data: data["evaluator"].update(revision="latest"), "고정 판"),
        (lambda data: data["predictions"].pop(), "사례 36개"),
        (lambda data: data["predictions"][1].update(caseId="KEN001"), "caseId가 겹친다"),
        (lambda data: data["predictions"][-1].update(caseId="KEN999"), "모르는 caseId"),
        (lambda data: data["predictions"][0].update(label="maybe"), "가운데 하나"),
        (lambda data: data["predictions"][0].update(confidence=1.1), "0부터 1"),
        (lambda data: data["predictions"][0].update(label="abstain", confidence=0.2), "confidence는 0"),
        (lambda data: data["predictions"][0].update(goldLabel="supported"), "모르는 키"),
    ],
)
def testPredictionContractRejectsStaleMissingDuplicateAndLeakedData(change, message):
    data = oraclePredictions()
    change(data)
    with pytest.raises(ValueError, match=message):
        EntailmentPredictions.fromMapping(data)


def testEvaluationRevalidatesAHandBuiltPredictionObject():
    parsed = EntailmentPredictions.fromMapping(oraclePredictions())
    invalid = replace(parsed, predictions=parsed.predictions[:-1])
    with pytest.raises(ValueError, match="사례 36개"):
        evaluateEntailment(invalid)


def testBenchmarkGateDetectsTextVoteLicenseAndDigestMutations():
    for mutation, message in (
        (lambda data: data["cases"][0].update(evidenceExcerpt="변조"), "문장 SHA256"),
        (lambda data: data["cases"][0]["annotation"].update(agreeingVotes=4), "합의 수"),
        (lambda data: data["cases"][0].update(license="MIT"), "라이선스"),
        (lambda data: data.update(contentSha256="0" * 64), "contentSha256"),
    ):
        data = deepcopy(shippedBenchmark())
        mutation(data)
        with pytest.raises(ValueError, match=message):
            checkedBenchmark(data)


def testPublishedSchemasNameGoldFreePredictionsAndLicensedBenchmark():
    dataRoot = ROOT / "src" / "hanlint" / "data"
    predictions = json.loads((dataRoot / "entailmentPredictions.schema.json").read_text(encoding="utf-8"))
    benchmark = json.loads((dataRoot / "evidenceEntailmentBenchmark.schema.json").read_text(encoding="utf-8"))
    predictionItem = predictions["properties"]["predictions"]["items"]
    assert set(predictionItem["required"]) == {"caseId", "label", "confidence"}
    assert "goldLabel" not in predictionItem["properties"] and predictions["properties"]["predictions"]["minItems"] == 36
    assert benchmark["properties"]["source"]["properties"]["license"]["const"] == "CC-BY-SA-4.0"
    assert benchmark["properties"]["cases"]["minItems"] == benchmark["properties"]["cases"]["maxItems"] == 36
