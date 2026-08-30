from pathlib import Path

import pytest

from hanlint.config import Config, loadConfig
from hanlint.data import exemplarFor


def testDefaultsAreTheTruth():
    config = Config()
    assert config.nounPileMin == 5
    assert config.enabled("deixis")


def testFromMappingSetsKnownKeys():
    config = Config.fromMapping(
        {"disable": ["nounPile"], "fragmentRun": 2, "keywordField": "primaryKeyword", "ignoreFences": [" Course-Scene "]}
    )
    assert not config.enabled("nounPile")
    assert config.fragmentRun == 2
    assert config.keywordField == "primaryKeyword"
    assert config.ignoreFences == ["course-scene"]
    assert config.headingSentenceMaxLevel == 6 and config.bridgeRepeatMin == 3


def testFromMappingRejectsUnknownKeyAndRemovedAnalyzer():
    with pytest.raises(ValueError):
        Config.fromMapping({"nounPileMinimum": 3})
    # 0.0.7 까지 hanlint init 이 써 넣던 키. surface 는 조용히 넘기고 다른 값은 빠졌다고 알린다
    assert not hasattr(Config.fromMapping({"analyzer": "surface"}), "analyzer")
    with pytest.raises(ValueError, match="빠졌다"):
        Config.fromMapping({"analyzer": "kiwi"})
    # 배열 자리에 문자열을 주면 글자 단위로 쪼개져 조용히 무시된다. 실측: 검증에서 잡혔다
    with pytest.raises(ValueError):
        Config.fromMapping({"ignoreFences": "course-scene"})
    with pytest.raises(ValueError):
        Config.fromMapping({"introFields": "readerQuestion"})


def testLoadFindsHanlintTomlUpwards(tmp_path: Path):
    (tmp_path / "hanlint.toml").write_text('disable = ["dash"]\n', encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    config = loadConfig(start=nested)
    assert not config.enabled("dash")


def testLoadReadsPyprojectSection(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[tool.hanlint]\nendingRun = 6\n", encoding="utf-8")
    assert loadConfig(start=tmp_path).endingRun == 6


def testLoadWithoutFileGivesDefaults(tmp_path: Path):
    assert loadConfig(start=tmp_path) == Config()


def testProjectExemplarOverridesTheMatchingBuiltIn():
    config = Config.fromMapping(
        {
            "exemplars": [
                {
                    "rule": "translationese",
                    "before": "우리 조직의 전 문장입니다.",
                    "after": "우리 조직의 후 문장입니다.",
                    "moved": "조직의 동사로 바꿈",
                    "presets": ["docs"],
                }
            ]
        }
    )
    chosen = exemplarFor("translationese", "docs", config.exemplars)
    assert chosen and chosen.before == "우리 조직의 전 문장입니다."
    assert exemplarFor("translationese", "blog", config.exemplars).before != chosen.before

    direct = Config(exemplars=[config.exemplars[0]])
    assert direct.exemplars == config.exemplars

    defaultNounPile = Config.fromMapping(
        {
            "exemplars": [
                {
                    "rule": "nounPile",
                    "before": "프로젝트 기본 전입니다.",
                    "after": "프로젝트 기본 후입니다.",
                    "moved": "관계를 풀어 씀",
                }
            ]
        }
    )
    assert exemplarFor("nounPile", "blog", defaultNounPile.exemplars).before == "프로젝트 기본 전입니다."
    assert exemplarFor("nounPile", "docs", defaultNounPile.exemplars).before.startswith("사용자 인증")


def testProjectExemplarsRejectAmbiguousOrUnknownEntries():
    exemplar = {
        "rule": "translationese",
        "before": "전 문장입니다.",
        "after": "후 문장입니다.",
        "moved": "서술어로 바꿈",
        "presets": ["blog"],
    }
    with pytest.raises(ValueError, match="프리셋이 겹친다"):
        Config.fromMapping({"exemplars": [exemplar, exemplar]})
    with pytest.raises(ValueError, match="모르는 규칙"):
        Config.fromMapping({"exemplars": [{**exemplar, "rule": "noSuchRule"}]})
    with pytest.raises(ValueError, match="비지 않은 문자열"):
        Config.fromMapping({"exemplars": [{**exemplar, "after": ""}]})


def testLoadReadsProjectExemplarArrayTable(tmp_path: Path):
    (tmp_path / "hanlint.toml").write_text(
        '[[exemplars]]\nrule = "translationese"\nbefore = "전입니다."\nafter = "후입니다."\n'
        'moved = "서술어로 바꿈"\npresets = ["blog"]\n',
        encoding="utf-8",
    )
    config = loadConfig(start=tmp_path)
    assert config.exemplars[0].rule == "translationese"
