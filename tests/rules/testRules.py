"""모든 규칙 fixture 를 돌린다. catch 는 잡히고 spare 는 안 잡혀야 한다.

fixture 가 없는 규칙과 규칙이 없는 fixture 도 여기서 잡는다. 규칙과 fixture 는 항상 짝이다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hanlint.config import Config
from hanlint.rules import ruleNames
from tests.conftest import expandTokens, findingsOf

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "rules"


def fixtureFiles() -> list[Path]:
    return sorted(FIXTURES.glob("*.json"))


def loadFixture(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["rule"] == path.stem, f"{path.name} 의 rule 이 파일 이름과 다르다"
    assert data.get("catch") and data.get("spare"), f"{path.name} 은 catch 와 spare 가 둘 다 있어야 한다"
    return data


@pytest.mark.parametrize("path", fixtureFiles(), ids=lambda p: p.stem)
def testFixture(path: Path):
    data = loadFixture(path)
    config = Config.fromMapping(data.get("config", {}))
    for text in data["catch"]:
        rules = [f.rule for f in findingsOf(expandTokens(text), config)]
        assert data["rule"] in rules, f"잡아야 하는데 안 잡았다: {text!r} → {rules}"
    for text in data["spare"]:
        rules = [f.rule for f in findingsOf(expandTokens(text), config)]
        assert data["rule"] not in rules, f"잡지 말아야 하는데 잡았다: {text!r}"


def testCalqueFrameBuiltinIsNoticeAndProjectEntryIsError():
    """기본 짝은 문맥을 보고 정할 notice 이고 프로젝트가 설정으로 더한 짝은 error 다. screenWord 와 같은 나눔이다."""
    text = "캐스팅 장갑은 아직 원투 글에 잇지 못했습니다. 할 일 판의 이 일은 아직 닫지 않았습니다."
    builtin = [f for f in findingsOf(text) if f.rule == "calqueFrame"]
    assert [(f.severity, f.fix) for f in builtin] == [("notice", None)]
    config = Config(
        dictionary={"calqueFrame": [{"pattern": "할 일 판", "fix": "투두리스트", "why": "는 이 프로젝트에서 투두리스트다"}]}
    )
    project = [f for f in findingsOf(text, config) if f.rule == "calqueFrame"]
    assert [f.severity for f in project] == ["notice", "error"]
    assert project[1].fix == "투두리스트의 이 일은 아직 닫지 않았습니다."


def testCalqueFrameNamesOneSentenceOnce():
    """`상품을` 과 `글에` 가 둘 다 잇다 의 앞말이어도 한 문장의 한 짝은 한 번만 짚는다 (unless 가 둘째 항목을 넘긴다)."""
    found = [f for f in findingsOf("돈값트리에 있던 상품을 세 글에 이었습니다.") if f.rule == "calqueFrame"]
    assert [f.why.split("`")[1] for f in found] == ["글에 이었"]


def testEveryRuleHasAFixtureAndEveryFixtureARule():
    rules = set(ruleNames())
    fixtures = {p.stem for p in fixtureFiles()}
    assert rules - fixtures == set(), f"fixture 가 없는 규칙: {sorted(rules - fixtures)}"
    assert fixtures - rules == set(), f"규칙이 없는 fixture: {sorted(fixtures - rules)}"
