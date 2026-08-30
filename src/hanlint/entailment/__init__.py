"""사람 합의 한국어 근거 쌍으로 외부 함의 평가기의 예측과 기권을 잰다."""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from functools import cache
from hashlib import sha256
from unicodedata import is_normalized

from ..data.load import loadJson

BENCHMARK_VERSION = 1
BENCHMARK_FILE = "evidenceEntailmentV1.json"
BENCHMARK_ID = "klue-nli-v1.1-dev-balanced-36"
BENCHMARK_SHA256 = "864e8af5bb88e16521e630c9f8987b32b36916c1042fee6a8ee54e76d7d8f5d8"
SOURCE_REVISION = "3efd98708a40ff49251fddde35453f8fbb11f536"
SOURCE_SHA256 = "0699db82be17766b26e199864e6260443e17ec6e91d1870e876419e388f245b1"
SOURCE_URL = (
    f"https://raw.githubusercontent.com/KLUE-benchmark/KLUE/{SOURCE_REVISION}/klue_benchmark/klue-nli-v1.1/klue-nli-v1.1_dev.json"
)
SOURCE_NAMES = ("NSMC", "airbnb", "policy", "wikinews", "wikipedia", "wikitree")
GOLD_LABELS = ("supported", "contradicted", "insufficient")
PREDICTION_LABELS = (*GOLD_LABELS, "abstain")
EVALUATOR_KINDS = ("human", "llm", "rule")
CASE_COUNT = 36
ENTAILMENT_MEANING = (
    "이 결과는 고정 KLUE-NLI 파생 36개에서 근거 조각과 원자 사실의 문맥상 관계만 잰다. "
    "출처나 fact의 진실, 글 품질과 다른 자료에서의 일반 성능을 보장하지 않는다"
)


def stableDigest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode()).hexdigest()


def exactKeys(data: object, expected: set[str], where: str) -> dict:
    if not isinstance(data, dict):
        raise ValueError(f"{where}는 JSON 객체다")
    unknown = sorted(set(data) - expected)
    missing = sorted(expected - set(data))
    if unknown:
        raise ValueError(f"{where}의 모르는 키: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{where}의 빠진 키: {', '.join(missing)}")
    return data


def checkedString(value: object, where: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{where}는 양끝 공백 없는 문자열이다")
    if not is_normalized("NFC", value):
        raise ValueError(f"{where}는 NFC 문자열이어야 한다")
    return value


def checkedSha(value: object, where: str) -> str:
    value = checkedString(value, where)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{where}는 소문자 SHA256이다")
    return value


def checkedLabel(value: object, choices: tuple[str, ...], where: str) -> str:
    value = checkedString(value, where)
    if value not in choices:
        raise ValueError(f"{where}는 {', '.join(choices)} 가운데 하나다")
    return value


def checkedBenchmark(data: object) -> dict:
    data = exactKeys(
        data,
        {"version", "kind", "benchmarkId", "source", "selection", "cases", "contentSha256"},
        "함의 benchmark",
    )
    if (
        isinstance(data["version"], bool)
        or not isinstance(data["version"], int)
        or data["version"] != BENCHMARK_VERSION
        or data["kind"] != "hanlint.evidenceEntailmentBenchmark"
    ):
        raise ValueError("함의 benchmark의 version 또는 kind가 다르다")
    benchmarkId = checkedString(data["benchmarkId"], "benchmarkId")
    source = exactKeys(
        data["source"],
        {"name", "repositoryUrl", "paperUrl", "sourceUrl", "revision", "sourceSha256", "license", "attribution"},
        "benchmark source",
    )
    for name in ("name", "repositoryUrl", "paperUrl", "sourceUrl", "revision", "license", "attribution"):
        checkedString(source[name], f"source.{name}")
    checkedSha(source["sourceSha256"], "source.sourceSha256")
    if source != {
        "name": "KLUE-NLI v1.1 dev",
        "repositoryUrl": "https://github.com/KLUE-benchmark/KLUE",
        "paperUrl": "https://arxiv.org/html/2105.09680v4",
        "sourceUrl": SOURCE_URL,
        "revision": SOURCE_REVISION,
        "sourceSha256": SOURCE_SHA256,
        "license": "CC-BY-SA-4.0",
        "attribution": "KLUE Benchmark contributors",
    }:
        raise ValueError("benchmark source가 고정 KLUE-NLI 판·라이선스와 다르다")
    selection = exactKeys(
        data["selection"],
        {
            "method",
            "sources",
            "sourceLabels",
            "labelMap",
            "casesPerSourceLabel",
            "minimumAgreement",
            "premiseDuplicates",
            "hypothesisDuplicates",
        },
        "benchmark selection",
    )
    checkedString(selection["method"], "selection.method")
    sources = selection["sources"]
    if not isinstance(sources, list) or not sources:
        raise ValueError("selection.sources는 중복 없는 비지 않은 배열이다")
    for index, value in enumerate(sources, start=1):
        checkedString(value, f"selection.sources {index}번째")
    if len(set(sources)) != len(sources):
        raise ValueError("selection.sources는 중복 없는 비지 않은 배열이다")
    if sources != list(SOURCE_NAMES):
        raise ValueError("selection.sources가 고정 여섯 source와 다르다")
    if selection["sourceLabels"] != ["contradiction", "entailment", "neutral"]:
        raise ValueError("selection.sourceLabels가 고정 KLUE label과 다르다")
    if selection["labelMap"] != {
        "contradiction": "contradicted",
        "entailment": "supported",
        "neutral": "insufficient",
    }:
        raise ValueError("selection.labelMap이 공개 label 계약과 다르다")
    if (
        selection["casesPerSourceLabel"] != 2
        or selection["minimumAgreement"] != 4
        or selection["premiseDuplicates"] != 0
        or selection["hypothesisDuplicates"] != 0
    ):
        raise ValueError("selection의 수량·합의·중복 계약이 다르다")
    cases = data["cases"]
    if not isinstance(cases, list) or len(cases) != CASE_COUNT:
        raise ValueError(f"함의 benchmark는 사례 {CASE_COUNT}개다")
    bins = Counter()
    excerptHashes = set()
    factHashes = set()
    sourceGuids = set()
    for index, item in enumerate(cases, start=1):
        where = f"함의 case {index}번째"
        item = exactKeys(
            item,
            {
                "id",
                "sourceGuid",
                "domain",
                "evidenceExcerpt",
                "atomicFact",
                "goldLabel",
                "annotation",
                "sourceUrl",
                "revision",
                "locator",
                "excerptSha256",
                "factSha256",
                "license",
                "caseSha256",
            },
            where,
        )
        if item["id"] != f"KEN{index:03d}":
            raise ValueError(f"{where} id가 순서와 다르다")
        sourceGuid = checkedString(item["sourceGuid"], f"{where}.sourceGuid")
        if sourceGuid in sourceGuids:
            raise ValueError("함의 benchmark의 sourceGuid가 겹친다")
        sourceGuids.add(sourceGuid)
        domain = checkedString(item["domain"], f"{where}.domain")
        if domain not in sources:
            raise ValueError(f"{where}.domain이 selection.sources에 없다")
        excerpt = checkedString(item["evidenceExcerpt"], f"{where}.evidenceExcerpt")
        fact = checkedString(item["atomicFact"], f"{where}.atomicFact")
        goldLabel = checkedLabel(item["goldLabel"], GOLD_LABELS, f"{where}.goldLabel")
        annotation = exactKeys(
            item["annotation"],
            {"authorLabel", "validatorLabels", "agreeingVotes", "totalVotes"},
            f"{where}.annotation",
        )
        authorLabel = checkedLabel(annotation["authorLabel"], GOLD_LABELS, f"{where}.annotation.authorLabel")
        validatorLabels = annotation["validatorLabels"]
        if not isinstance(validatorLabels, list) or len(validatorLabels) != 4:
            raise ValueError(f"{where}.annotation.validatorLabels는 네 표다")
        validators = [
            checkedLabel(value, GOLD_LABELS, f"{where}.annotation.validatorLabels {voteIndex}번째")
            for voteIndex, value in enumerate(validatorLabels, start=1)
        ]
        agreement = sum(value == goldLabel for value in (authorLabel, *validators))
        if annotation["totalVotes"] != 5 or annotation["agreeingVotes"] != agreement or agreement < 4:
            raise ValueError(f"{where}.annotation의 다섯 표와 합의 수가 맞지 않는다")
        excerptSha = checkedSha(item["excerptSha256"], f"{where}.excerptSha256")
        factSha = checkedSha(item["factSha256"], f"{where}.factSha256")
        if excerptSha != sha256(excerpt.encode()).hexdigest() or factSha != sha256(fact.encode()).hexdigest():
            raise ValueError(f"{where}의 문장 SHA256이 다르다")
        if excerptSha in excerptHashes or factSha in factHashes:
            raise ValueError("함의 benchmark의 전제나 가설이 겹친다")
        excerptHashes.add(excerptSha)
        factHashes.add(factSha)
        if (
            item["sourceUrl"] != source["sourceUrl"]
            or item["revision"] != source["revision"]
            or item["locator"] != sourceGuid
            or item["license"] != source["license"]
        ):
            raise ValueError(f"{where}의 출처 판·locator·라이선스가 정본과 다르다")
        caseSha = checkedSha(item["caseSha256"], f"{where}.caseSha256")
        if caseSha != stableDigest({key: value for key, value in item.items() if key != "caseSha256"}):
            raise ValueError(f"{where}.caseSha256이 내용과 다르다")
        bins[(domain, goldLabel)] += 1
    expectedBins = {(sourceName, label): 2 for sourceName in sources for label in GOLD_LABELS}
    if dict(bins) != expectedBins:
        raise ValueError("함의 benchmark의 source·label 균형이 다르다")
    contentSha = checkedSha(data["contentSha256"], "benchmark.contentSha256")
    if contentSha != stableDigest({key: value for key, value in data.items() if key != "contentSha256"}):
        raise ValueError("benchmark.contentSha256이 내용과 다르다")
    if contentSha != BENCHMARK_SHA256:
        raise ValueError("benchmark.contentSha256이 고정 평가판과 다르다")
    if benchmarkId != BENCHMARK_ID:
        raise ValueError("benchmarkId가 고정 평가판과 다르다")
    return data


@cache
def shippedBenchmark() -> dict:
    return checkedBenchmark(loadJson(BENCHMARK_FILE))


@dataclass(frozen=True)
class EntailmentPrediction:
    caseId: str
    label: str
    confidence: float

    def asDict(self) -> dict:
        return {"caseId": self.caseId, "label": self.label, "confidence": self.confidence}


@dataclass(frozen=True)
class EntailmentPredictions:
    benchmarkId: str
    benchmarkSha256: str
    evaluatorId: str
    evaluatorKind: str
    evaluatorRevision: str
    promptSha256: str
    predictions: tuple[EntailmentPrediction, ...]

    @classmethod
    def fromMapping(cls, data: object) -> EntailmentPredictions:
        data = exactKeys(
            data,
            {"version", "kind", "benchmarkId", "benchmarkSha256", "evaluator", "predictions"},
            "함의 predictions",
        )
        if (
            isinstance(data["version"], bool)
            or not isinstance(data["version"], int)
            or data["version"] != BENCHMARK_VERSION
            or data["kind"] != "hanlint.entailmentPredictions"
        ):
            raise ValueError("함의 predictions의 version 또는 kind가 다르다")
        benchmark = shippedBenchmark()
        benchmarkId = checkedString(data["benchmarkId"], "predictions.benchmarkId")
        benchmarkSha = checkedSha(data["benchmarkSha256"], "predictions.benchmarkSha256")
        if benchmarkId != benchmark["benchmarkId"] or benchmarkSha != benchmark["contentSha256"]:
            raise ValueError("함의 predictions가 고정 benchmark 판을 가리키지 않는다")
        evaluator = exactKeys(
            data["evaluator"],
            {"id", "kind", "revision", "promptSha256"},
            "predictions.evaluator",
        )
        evaluatorId = checkedString(evaluator["id"], "evaluator.id")
        evaluatorKind = checkedLabel(evaluator["kind"], EVALUATOR_KINDS, "evaluator.kind")
        evaluatorRevision = checkedString(evaluator["revision"], "evaluator.revision")
        if evaluatorRevision.casefold() in {"head", "latest", "main", "master"}:
            raise ValueError("evaluator.revision은 움직이는 별칭이 아니라 고정 판이어야 한다")
        promptSha = checkedSha(evaluator["promptSha256"], "evaluator.promptSha256")
        rawPredictions = data["predictions"]
        if not isinstance(rawPredictions, list) or len(rawPredictions) != CASE_COUNT:
            raise ValueError(f"predictions는 사례 {CASE_COUNT}개의 예측 배열이다")
        predictions = {}
        for index, item in enumerate(rawPredictions, start=1):
            item = exactKeys(item, {"caseId", "label", "confidence"}, f"prediction {index}번째")
            caseId = checkedString(item["caseId"], f"prediction {index}번째.caseId")
            if caseId in predictions:
                raise ValueError(f"prediction caseId가 겹친다: {caseId}")
            label = checkedLabel(item["label"], PREDICTION_LABELS, f"prediction {index}번째.label")
            confidence = item["confidence"]
            if (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not math.isfinite(confidence)
                or not 0 <= confidence <= 1
            ):
                raise ValueError(f"prediction {index}번째.confidence는 0부터 1까지 유한한 수다")
            if label == "abstain" and confidence != 0:
                raise ValueError(f"prediction {index}번째가 abstain이면 confidence는 0이다")
            predictions[caseId] = EntailmentPrediction(caseId, label, float(confidence))
        caseIds = [case["id"] for case in benchmark["cases"]]
        unknown = sorted(set(predictions) - set(caseIds))
        missing = sorted(set(caseIds) - set(predictions))
        if unknown:
            raise ValueError(f"predictions의 모르는 caseId: {', '.join(unknown)}")
        if missing:
            raise ValueError(f"predictions의 빠진 caseId: {', '.join(missing)}")
        return cls(
            benchmarkId,
            benchmarkSha,
            evaluatorId,
            evaluatorKind,
            evaluatorRevision,
            promptSha,
            tuple(predictions[caseId] for caseId in caseIds),
        )

    @property
    def digest(self) -> str:
        return stableDigest(self.asDict())

    def asDict(self) -> dict:
        return {
            "version": BENCHMARK_VERSION,
            "kind": "hanlint.entailmentPredictions",
            "benchmarkId": self.benchmarkId,
            "benchmarkSha256": self.benchmarkSha256,
            "evaluator": {
                "id": self.evaluatorId,
                "kind": self.evaluatorKind,
                "revision": self.evaluatorRevision,
                "promptSha256": self.promptSha256,
            },
            "predictions": [prediction.asDict() for prediction in self.predictions],
        }


@dataclass(frozen=True)
class EntailmentEvaluationResult:
    benchmarkId: str
    benchmarkSha256: str
    predictionSha256: str
    evaluator: dict
    metrics: dict

    def asDict(self) -> dict:
        data = {
            "version": BENCHMARK_VERSION,
            "kind": "hanlint.entailmentBenchmarkResult",
            "benchmarkId": self.benchmarkId,
            "benchmarkSha256": self.benchmarkSha256,
            "predictionSha256": self.predictionSha256,
            "evaluator": self.evaluator,
            "metrics": self.metrics,
            "meaning": ENTAILMENT_MEANING,
        }
        data["resultSha256"] = stableDigest(data)
        return data


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def entailmentCases() -> dict:
    """gold와 표를 빼고 평가기에 줄 36개 근거 쌍만 낸다."""
    benchmark = shippedBenchmark()
    data = {
        "version": BENCHMARK_VERSION,
        "kind": "hanlint.entailmentCases",
        "benchmarkId": benchmark["benchmarkId"],
        "benchmarkSha256": benchmark["contentSha256"],
        "labels": {
            "supported": "근거 조각이 참이면 원자 사실도 반드시 참이다",
            "contradicted": "근거 조각이 참이면 원자 사실은 반드시 거짓이다",
            "insufficient": "근거 조각만으로 원자 사실의 참과 거짓을 정할 수 없다",
            "abstain": "관계를 확실히 고를 수 없어 답하지 않는다",
        },
        "source": {
            "name": benchmark["source"]["name"],
            "revision": benchmark["source"]["revision"],
            "license": benchmark["source"]["license"],
            "attribution": benchmark["source"]["attribution"],
        },
        "cases": [
            {
                "caseId": case["id"],
                "domain": case["domain"],
                "evidenceExcerpt": case["evidenceExcerpt"],
                "atomicFact": case["atomicFact"],
            }
            for case in benchmark["cases"]
        ],
        "instruction": "각 caseId에 label과 0부터 1까지 confidence를 하나씩 낸다. abstain의 confidence는 0이다",
        "meaning": "두 문장의 문맥상 관계만 묻는다. 문장 자체가 세상에서 참인지는 묻지 않는다",
    }
    data["contentSha256"] = stableDigest(data)
    return data


def evaluateEntailment(predictions: EntailmentPredictions | dict) -> EntailmentEvaluationResult:
    """gold를 공개하지 않고 3분류와 기권 지표를 결정적으로 집계한다."""
    if isinstance(predictions, EntailmentPredictions):
        predictions = EntailmentPredictions.fromMapping(predictions.asDict())
    elif isinstance(predictions, dict):
        predictions = EntailmentPredictions.fromMapping(predictions)
    else:
        raise ValueError("evaluateEntailment 입력은 EntailmentPredictions 또는 JSON 객체다")
    benchmark = shippedBenchmark()
    gold = {case["id"]: case["goldLabel"] for case in benchmark["cases"]}
    matrix = {label: {predicted: 0 for predicted in PREDICTION_LABELS} for label in GOLD_LABELS}
    correct = 0
    answered = 0
    ranked = []
    for prediction in predictions.predictions:
        goldLabel = gold[prediction.caseId]
        matrix[goldLabel][prediction.label] += 1
        if prediction.label == "abstain":
            continue
        answered += 1
        isCorrect = prediction.label == goldLabel
        correct += isCorrect
        ranked.append((prediction.confidence, prediction.caseId, isCorrect))
    perClass = {}
    f1Values = []
    for label in GOLD_LABELS:
        truePositive = matrix[label][label]
        falsePositive = sum(matrix[other][label] for other in GOLD_LABELS if other != label)
        falseNegative = sum(matrix[label][other] for other in PREDICTION_LABELS if other != label)
        denominator = 2 * truePositive + falsePositive + falseNegative
        f1 = 2 * truePositive / denominator if denominator else 0.0
        f1Values.append(f1)
        perClass[label] = {
            "truePositive": truePositive,
            "falsePositive": falsePositive,
            "falseNegative": falseNegative,
            "precision": ratio(truePositive, truePositive + falsePositive),
            "recall": ratio(truePositive, truePositive + falseNegative),
            "f1": round(f1, 4),
        }
    riskCoverageCurve = []
    cumulativeAnswered = 0
    cumulativeErrors = 0
    for confidence in sorted({item[0] for item in ranked}, reverse=True):
        atThreshold = [item for item in ranked if item[0] == confidence]
        cumulativeAnswered += len(atThreshold)
        cumulativeErrors += sum(not item[2] for item in atThreshold)
        riskCoverageCurve.append(
            {
                "threshold": confidence,
                "answered": cumulativeAnswered,
                "errors": cumulativeErrors,
                "coverage": ratio(cumulativeAnswered, CASE_COUNT),
                "selectiveRisk": ratio(cumulativeErrors, cumulativeAnswered),
            }
        )
    metrics = {
        "totalCases": CASE_COUNT,
        "answered": answered,
        "abstained": CASE_COUNT - answered,
        "coverage": ratio(answered, CASE_COUNT),
        "selectedAccuracy": {"correct": correct, "answered": answered, "ratio": ratio(correct, answered)},
        "selectiveRisk": {"errors": answered - correct, "answered": answered, "ratio": ratio(answered - correct, answered)},
        "confusionMatrix": matrix,
        "perClass": perClass,
        "macroF1": round(sum(f1Values) / len(f1Values), 4),
        "riskCoverageCurve": riskCoverageCurve,
    }
    return EntailmentEvaluationResult(
        predictions.benchmarkId,
        predictions.benchmarkSha256,
        predictions.digest,
        {
            "id": predictions.evaluatorId,
            "kind": predictions.evaluatorKind,
            "revision": predictions.evaluatorRevision,
            "promptSha256": predictions.promptSha256,
        },
        metrics,
    )


__all__ = [
    "BENCHMARK_VERSION",
    "BENCHMARK_ID",
    "BENCHMARK_SHA256",
    "ENTAILMENT_MEANING",
    "EVALUATOR_KINDS",
    "GOLD_LABELS",
    "PREDICTION_LABELS",
    "EntailmentEvaluationResult",
    "EntailmentPrediction",
    "EntailmentPredictions",
    "entailmentCases",
    "evaluateEntailment",
]
