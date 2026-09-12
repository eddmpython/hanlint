"""브라우저 수정 후보와 문장 대응을 Python 정본과 대조한다."""

from __future__ import annotations

import json
import random
import shutil
import subprocess
from difflib import SequenceMatcher
from pathlib import Path

import pytest

from hanlint import learnOperationText, learnText

ROOT = Path(__file__).resolve().parents[2]


def runNode(code: str, data: list) -> list:
    """표준 입력으로 사례를 전달하고 JSON 결과를 받는다."""
    if not shutil.which("node"):
        pytest.skip("node가 없다")
    result = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        input=json.dumps(data),
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def testSentenceRangesMatchPythonSequenceMatcher():
    rng = random.Random(410)
    cases = [
        [rng.choices(list("abcde"), k=rng.randrange(18)), rng.choices(list("abcde"), k=rng.randrange(18))] for _ in range(120)
    ]
    actual = runNode(
        'import {changedRanges} from "./npm/src/learn/pairs.js"; '
        'import {readFileSync} from "node:fs"; '
        'console.log(JSON.stringify(JSON.parse(readFileSync(0,"utf8")).map(([a,b])=>changedRanges(a,b))));',
        cases,
    )
    expected = [
        [[a, b, c, d] for tag, a, b, c, d in SequenceMatcher(None, left, right, autojunk=False).get_opcodes() if tag != "equal"]
        for left, right in cases
    ]
    assert actual == expected


def testLearnCandidatesMatchPython():
    cases = [
        ["결과가 저장되어집니다.", "결과가 저장됩니다."],
        ["설계에 대한 이해가 필요합니다.", "설계를 알아야 합니다. 예제를 직접 실행합니다."],
        ["핵심은 `make_qr`입니다.", "`make_qr`가 QR코드를 만듭니다."],
        ["첫 렌더 결과입니다.", "첫 렌더링 결과입니다."],
        ["2개가 있습니다.", "3개가 있습니다."],
        ["설계에 대한 이해가 필요합니다.", "새 설계에 대한 이해가 필요합니다."],
        ["설계에 대한 이해가 필요합니다. 결과를 기록합니다.", "설계를 알아야 합니다. 결과는 표에 적습니다. 담당자가 검토합니다."],
    ]
    actual = runNode(
        'import {learnText} from "./npm/src/index.js"; import {readFileSync} from "node:fs"; '
        'console.log(JSON.stringify(JSON.parse(readFileSync(0,"utf8")).map(([a,b])=>learnText(a,b))));',
        cases,
    )
    expected = [
        {
            "exemplars": [item.asDict() for item in learnText(before, after)],
            "operations": [item.asDict() for item in learnOperationText(before, after)],
        }
        for before, after in cases
    ]
    assert actual == expected
