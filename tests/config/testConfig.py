from pathlib import Path

import pytest

from hanlint.config import Config, loadConfig


def testDefaultsAreTheTruth():
    config = Config()
    assert config.analyzer == "surface"
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


def testFromMappingRejectsUnknownKeyAndBadAnalyzer():
    with pytest.raises(ValueError):
        Config.fromMapping({"nounPileMinimum": 3})
    with pytest.raises(ValueError):
        Config.fromMapping({"analyzer": "mecab"})
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
