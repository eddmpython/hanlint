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


def testEveryRuleHasAFixtureAndEveryFixtureARule():
    rules = set(ruleNames())
    fixtures = {p.stem for p in fixtureFiles()}
    assert rules - fixtures == set(), f"fixture 가 없는 규칙: {sorted(rules - fixtures)}"
    assert fixtures - rules == set(), f"규칙이 없는 fixture: {sorted(fixtures - rules)}"
