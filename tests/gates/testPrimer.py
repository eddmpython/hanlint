"""primer 게이트. 켜진 규칙이 하나도 빠지지 않고, 후는 전부 error 0 이고, 한 장은 LINE_LIMIT 안이다.

primer 는 글을 쓰기 전의 AI 가 그대로 읽고 본뜨는 것이라 틀리면 나쁜 글을 퍼뜨린다. 본보기 게이트
(testExemplars) 가 본보기 자체를 보고, 여기는 primer 가 그 본보기를 빠뜨리거나 잘못 고르지 않는지 본다.
"""

from __future__ import annotations

import json

import pytest

from hanlint.analysis.grammar import REGISTERS
from hanlint.cli.commands.primer import LINE_LIMIT, PrimerEntry, flat, primerEntries, renderPrimer
from hanlint.cli.main import main
from hanlint.config import PRESET_NAMES, Config
from hanlint.rules import CATEGORY_TITLES, ruleNames
from hanlint.rules.registry import REQUIRED_SECTIONS, docSection
from tests.conftest import findingsOf


def enabledRules(config: Config) -> list[str]:
    """그 설정에서 도는 규칙 이름."""
    off = set(config.offRules())
    return [name for name in ruleNames() if name not in off]


def missingRules(entries: list[PrimerEntry], config: Config) -> list[str]:
    """켜졌는데 한 장에 없는 규칙. 비어 있어야 정상이다."""
    present = {entry.rule for entry in entries}
    return [name for name in enabledRules(config) if name not in present]


def afterErrors(text: str, config: Config) -> list[str]:
    """후가 그 설정에서 내는 error 규칙. 비어 있어야 정상이다."""
    return sorted({f.rule for f in findingsOf(text, config) if f.severity == "error"})


@pytest.mark.parametrize("preset", PRESET_NAMES)
def testEveryEnabledRuleAppearsOnce(preset: str) -> None:
    config = Config(preset=preset)
    entries = primerEntries(config)
    names = [entry.rule for entry in entries]
    assert missingRules(entries, config) == []
    assert len(names) == len(set(names)) == len(enabledRules(config))
    assert all(entry.fix and "\n" not in entry.fix for entry in entries)


@pytest.mark.parametrize("register", REGISTERS)
@pytest.mark.parametrize("preset", PRESET_NAMES)
def testAfterPassesUnderThatPreset(preset: str, register: str) -> None:
    config = Config(preset=preset)
    bad = {entry.rule: afterErrors(entry.after, config) for entry in primerEntries(config, register)}
    assert {rule: errors for rule, errors in bad.items() if errors} == {}


@pytest.mark.parametrize("register", REGISTERS)
@pytest.mark.parametrize("preset", PRESET_NAMES)
def testFitsOnOnePage(preset: str, register: str) -> None:
    config = Config(preset=preset)
    text = renderPrimer(primerEntries(config, register), preset, register)
    assert len(text.splitlines()) <= LINE_LIMIT


def testCatchesMissingRule() -> None:
    config = Config(preset="blog")
    entries = primerEntries(config)
    assert missingRules(entries[1:], config) == [entries[0].rule]


def testCatchesBadAfter() -> None:
    assert "doublePassive" in afterErrors("결과가 저장되어집니다.", Config(preset="blog"))


def testFlattensLineBreaksVisibly() -> None:
    assert flat("## 절\n\n첫  문단.\n") == "## 절 ¶ 첫 문단."
    assert flat("한 줄.") == "한 줄."


def testCliRendersTextAndJson(capsys) -> None:
    assert main(["primer", "--preset", "docs"]) == 0
    text = capsys.readouterr().out
    assert text.startswith("hanlint primer  docs 종류, 합니다체")
    assert main(["primer", "--preset", "chat", "--format", "json", "--register", "한다"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["preset"] == "chat" and data["register"] == "한다"
    assert len(data["rules"]) == len(enabledRules(Config(preset="chat")))


SAMPLE_DOC = "첫 줄.\n\n왜: 이유.\n어디서: 출처.\n고치기: 하나.\n    둘.\n안 잡는 것: 셋."
"""네 절이 있는 기술서. 고치기 절은 두 줄이고 바로 뒤에 다음 절이 온다."""


def testDocSectionStopsAtNextLabel() -> None:
    assert docSection(SAMPLE_DOC, "고치기:") == "하나. 둘."
    assert docSection(SAMPLE_DOC, "안 잡는 것:") == "셋."
    assert docSection(SAMPLE_DOC, "왜:") == "이유."


def testFixNeverCarriesAnotherSection() -> None:
    for entry in primerEntries(Config(preset="blog")):
        assert not any(label in entry.fix for label in REQUIRED_SECTIONS), entry.rule


@pytest.mark.parametrize("preset", PRESET_NAMES)
def testOnePageShape(preset: str) -> None:
    """머리글 하나, 부류마다 빈 줄과 제목, 규칙마다 한 줄, 빈 줄과 꼬리글. 그 밖의 줄은 없다."""
    entries = primerEntries(Config(preset=preset))
    categories = {entry.category for entry in entries}
    lines = renderPrimer(entries, preset, "합니다").splitlines()
    assert len(lines) == 1 + 2 * len(categories) + len(entries) + 2
    titles = set(CATEGORY_TITLES.values())
    assert len([line for line in lines if line.rsplit(" (", 1)[0] in titles]) == len(categories)
