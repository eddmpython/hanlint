from __future__ import annotations

import pytest

from hanlint import Config
from hanlint.report import renderWritingSpec, writingSpec


def row(spec, rowId: str):
    return next(item for item in spec.rows if item.id == rowId)


def testWritingSpecCombinesProfileAndEnabledRules():
    spec = writingSpec(Config(preset="blog"), "합니다", 800)

    assert spec.profile == "blog"
    assert spec.targetChars == 800
    assert row(spec, "amount").guidance == "문단 6개, 문단마다 문장 2~4개, 문장 11개 안팎"
    assert row(spec, "sentenceLength").basis == ("profile.blog.sentence.length", "rule.longSentence")
    assert "5개부터 nounPile이 지적" in row(spec, "nounRun").guidance
    assert row(spec, "question").basis == ("profile.blog.rates.question", "rule.noQuestion")
    assert [item.id for item in spec.rows] == [
        "amount",
        "sentenceLength",
        "endingRun",
        "commas",
        "euiCount",
        "nounRun",
        "newTopics",
        "connector",
        "numbers",
        "question",
    ]

    rendered = renderWritingSpec(spec)
    assert rendered.startswith("hanlint spec  blog 종류, 합니다체, 800자.")
    assert rendered.endswith("쓴 뒤 같은 설정으로 hanlint <글.md>를 실행해 Finding을 확인한다")


def testWritingSpecDoesNotClaimDisabledRules():
    config = Config(preset="report", disable={"longSentence", "nounPile"})
    spec = writingSpec(config, "한다")

    assert row(spec, "sentenceLength").basis == ("profile.report.sentence.length",)
    assert "longSentence" not in row(spec, "sentenceLength").guidance
    assert row(spec, "nounRun").basis == ("profile.report.sentence.nounRun",)
    assert "nounPile" not in row(spec, "nounRun").guidance
    assert row(spec, "question").guidance.startswith("규칙 요구 없음")


def testWritingSpecRejectsMissingProfileAndInvalidLength():
    with pytest.raises(ValueError, match="종류 프로파일이 없어"):
        writingSpec(Config(preset="chat"))
    with pytest.raises(ValueError, match="chars 는 1 이상"):
        writingSpec(targetChars=0)
