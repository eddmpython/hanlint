import json
import subprocess
import sys
from pathlib import Path

import pytest

from hanlint import Config, ContractV2, check, lintText, ruleNames, verifyPatch

ROOT = Path(__file__).resolve().parents[2]
FACTS = ["A사의 매출은 100억 원이다.", "B사의 매출은 200억 원이다.", "지원은 확정되지 않았다."]
TEXT = "## 실적\n\n" + " ".join(FACTS) + "\n\n금새 끝난다.\n\n다음 글은 내일 읽는다."


def contract(policy=None):
    return ContractV2(
        "독자",
        "실적 확인",
        FACTS,
        {"numbers": ["100", "200"], "urls": [], "code": [], "links": []},
        {"level": 2, "headings": ["실적"]},
        lockedFacts=FACTS,
        editPolicy=policy or {},
    )


def config():
    return Config(disable=set(ruleNames()) - {"spelling"})


def testLockedFactsDetectSwappedValuesAndNegationWithoutInventingMeaning():
    approved = contract()
    assert check(TEXT, approved, config()).missingFacts == ()
    swapped = TEXT.replace("100", "TEMP").replace("200", "100").replace("TEMP", "200")
    receipt = check(swapped, approved, config())
    assert receipt.surface.violationCount == 0
    assert receipt.missingFacts == tuple(FACTS[:2])
    assert check(TEXT.replace("확정되지 않았다", "확정됐다"), approved, config()).missingFacts == (FACTS[2],)
    with pytest.raises(ValueError, match="approved facts"):
        ContractV2("독자", "목표", [], approved.surface, approved.outline, lockedFacts=FACTS)


def testEditBudgetAcceptsLocalFixButRejectsUnrelatedRewrite():
    approved = contract({"spelling": {"maxChars": 2, "maxLines": 1}})
    patch = {"reason": "spelling", "before": "금새", "after": "금세"}
    result = verifyPatch(TEXT, patch, approved, config())
    assert result.verified
    assert result.resultText == TEXT.replace("금새", "금세")
    broad = {"reason": "spelling", "before": TEXT, "after": TEXT.replace("금새", "금세").replace("내일", "오늘")}
    rejected = verifyPatch(TEXT, broad, approved, config())
    assert not rejected.verified
    assert ("editPolicy", "changed range exceeds maxLines") in rejected.newContractIssues
    assert ("editPolicy", "changed range exceeds maxChars") in rejected.newContractIssues
    wrong = {"reason": "spelling", "before": "내일", "after": "오늘"}
    assert ("editPolicy", "changed range does not contain the Finding line") in verifyPatch(
        TEXT, wrong, approved, config()
    ).newContractIssues


def testPatchCannotTradeApprovedFactForOneLessSpellingFinding():
    patch = {"reason": "spelling", "before": TEXT, "after": TEXT.replace("금새", "금세").replace("확정되지 않았다", "확정됐다")}
    result = verifyPatch(TEXT, patch, contract(), config())
    assert not result.verified
    assert result.reasonReduced
    assert result.newContractIssues == (("lockedFacts", FACTS[2]),)


@pytest.mark.parametrize("value", [{"spelling": {"maxChars": True, "maxLines": 1}}, {"spelling": {"maxChars": 2}}, []])
def testMalformedBudgetsAreRejected(value):
    with pytest.raises(ValueError, match="editPolicy"):
        contract(value if value != [] else {"spelling": []})


def testBothRuntimesAgreeOnFactLocksBudgetRejectionAndHashes():
    approved = contract({"spelling": {"maxChars": 2, "maxLines": 1}})
    patch = {"reason": "spelling", "before": TEXT, "after": TEXT.replace("금새", "금세").replace("내일", "오늘")}
    script = """import {check, verifyPatch, configFromMapping} from './npm/src/index.js';
let data = ''; for await (const chunk of process.stdin) data += chunk;
const v = JSON.parse(data), c = configFromMapping(v.config);
console.log(JSON.stringify([check(v.text,v.contract,c).asDict(),verifyPatch(v.text,v.patch,v.contract,c).asDict()]));"""
    payload = {"text": TEXT, "contract": approved.asDict(), "patch": patch, "config": {"disable": sorted(config().disable)}}
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        check=True,
    )
    assert json.loads(completed.stdout) == [
        check(TEXT, approved, config()).asDict(),
        verifyPatch(TEXT, patch, approved, config()).asDict(),
    ]


@pytest.mark.parametrize(
    "rule,text",
    [
        ("noQuestion", "## 첫 절\n\n파일을 저장한다.\n\n## 다음 절\n\n결과를 확인한다."),
        ("nounPile", "가상환경 생성 후 패키지 설치 확인 절차를 따릅니다."),
    ],
)
def testStyleSignalsOnlyBlockUnderSelectedPolicy(rule, text):
    normal = [f for f in lintText(text) if f.rule == rule]
    strict = [f for f in lintText(text, Config(enforceStyle=[rule])) if f.rule == rule]
    assert normal and all(f.severity == "notice" for f in normal)
    assert strict and all(f.severity == "error" for f in strict)


def testSelectedStyleOverridesPresetButExplicitDisableStillWins():
    chosen = Config(preset="docs", enforceStyle=["noQuestion"])
    assert chosen.enabled("noQuestion")
    assert "noQuestion" not in chosen.offRules()
    chosen.disable.add("noQuestion")
    assert not chosen.enabled("noQuestion")


@pytest.mark.parametrize("field,value", [("lockedFacts", None), ("editPolicy", None), ("lockedFacts", "fact")])
def testContractRejectsInvalidOptionalFields(field, value):
    data = contract().asDict()
    data[field] = value
    with pytest.raises(ValueError):
        ContractV2.fromMapping(data)


@pytest.mark.parametrize("runtime", ["python", "node"])
def testCliRejectsTheSameUnsafeDraftAndPatch(runtime, tmp_path):
    approved = contract({"spelling": {"maxChars": 2, "maxLines": 1}})
    contractPath, draftPath, patchPath = [tmp_path / name for name in ("contract.json", "draft.md", "patch.json")]
    configPath = tmp_path / "hanlint.toml"
    configPath.write_text("disable = " + json.dumps(sorted(config().disable)), encoding="utf-8")
    contractPath.write_text(json.dumps(approved.asDict(), ensure_ascii=False), encoding="utf-8")
    draftPath.write_text(TEXT.replace("확정되지 않았다", "확정됐다"), encoding="utf-8")
    command = [sys.executable, "-X", "utf8", "-B", "-m", "hanlint"] if runtime == "python" else ["node", "npm/bin/hanlint.js"]
    receipt = subprocess.run(
        [*command, "check", str(contractPath), str(draftPath)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert receipt.returncode == 1, receipt.stderr
    assert json.loads(receipt.stdout)["missingFacts"] == [FACTS[2]]
    draftPath.write_text(TEXT, encoding="utf-8")
    patch = {"reason": "spelling", "before": TEXT, "after": TEXT.replace("금새", "금세").replace("내일", "오늘")}
    patchPath.write_text(json.dumps(patch, ensure_ascii=False), encoding="utf-8")
    receipt = subprocess.run(
        [*command, "verify-patch", str(contractPath), str(draftPath), str(patchPath)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert receipt.returncode == 1, receipt.stderr
    assert not json.loads(receipt.stdout)["verified"]
    assert draftPath.read_text(encoding="utf-8") == TEXT
