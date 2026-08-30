"""패턴을 뺀 초안에서 결정적 사실 가드가 일반 재시도보다 나은지 잰다."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from probeWritingLift import OLLAMA_ENDPOINT, readJson, sha256File, sha256Text, stableJson, writeJson  # noqa: E402
from probeWritingLiftAblation import (  # noqa: E402
    renderScore,
    runGeneration,
    runJudgments,
    scoreAll,
    scoreAutomatic,
)

from hanlint import Config, lintText  # noqa: E402

BASELINE = "dropPatterns"
CANDIDATES = ("retryRevision", "guardedRepair", "guardedLintRepair", "ledgerRewrite")
CONDITIONS = (BASELINE,) + CANDIDATES


def responseMapOf(responses: dict) -> dict[tuple[str, str], dict]:
    return {(item["taskId"], item["condition"]): item for item in responses["responses"]}


def automaticMapOf(automatic: dict) -> dict[tuple[str, str], dict]:
    return {(item["taskId"], item["condition"]): item for item in automatic["results"]}


def commonPrompt(task: dict, draft: str) -> str:
    return (
        "아래 원래 요구와 현재 초안을 대조해 완성 글을 한 번 작성한다. 사실, 수치, 이름, 명령과 링크를 "
        "보존하고 요구 밖의 사실이나 인과를 만들지 않는다. 메타 설명, 점검표, 작성 과정, 자기평가, 바깥 "
        "코드 펜스 없이 완성된 한국어 마크다운만 출력한다.\n\n"
        "<원래 요구>\n" + task["briefMarkdown"] + "</원래 요구>\n\n<현재 초안>\n" + draft + "\n</현재 초안>\n\n"
    )


def guardLines(task: dict, automatic: dict) -> list[str]:
    minimum, maximum = task["length"]
    lines = [
        f"현재 글자 수 {automatic['characterCount']}자, 허용 범위 {minimum}자 이상 {maximum}자 이하",
    ]
    if automatic["missingLiterals"]:
        lines.append("빠진 필수 표면: " + ", ".join(automatic["missingLiterals"]))
    if automatic["missingNumbers"]:
        lines.append("빠진 숫자 원자: " + ", ".join(automatic["missingNumbers"]))
    if automatic["extraNumbers"]:
        lines.append("요구에 없는 숫자 원자: " + ", ".join(automatic["extraNumbers"]))
    if automatic["forbiddenHits"]:
        lines.append("들어간 금지 주장: " + ", ".join(automatic["forbiddenHits"]))
    return lines


def retryPrompt(task: dict, draft: str) -> str:
    return commonPrompt(task, draft) + "초안의 장점을 살리면서 원래 요구를 더 충실히 만족하도록 고쳐라."


def guardedPrompt(task: dict, draft: str, automatic: dict, includeLint: bool) -> str:
    guards = "\n".join(f"- {line}" for line in guardLines(task, automatic))
    lintBlock = ""
    if includeLint:
        findings = lintText(draft, Config(preset=task["preset"]), path=f"{task['id']}.md")
        errors = [finding for finding in findings if finding.severity == "error"]
        if errors:
            rendered = "\n".join(f"- {finding.rule}: {finding.quote} / {finding.why}" for finding in errors)
            lintBlock = "\n\n<hanlint의 정확한 error 자리>\n" + rendered + "\n</hanlint의 정확한 error 자리>"
    return (
        commonPrompt(task, draft) + "기계가 찾은 다음 실패만 정확히 고친다. 필수 표면을 억지 목록으로 덧붙이지 말고 해당 사실의 "
        "문장에 자연스럽게 넣는다. 요구에 없는 숫자는 없애며 이미 맞는 사실은 바꾸지 않는다.\n\n"
        "<결정적 가드>\n" + guards + "\n</결정적 가드>" + lintBlock
    )


def ledgerPrompt(task: dict, draft: str) -> str:
    facts = "\n".join(f"- F{index}: {fact}" for index, fact in enumerate(task["facts"], start=1))
    mustInclude = ", ".join(task["mustInclude"])
    minimum, maximum = task["length"]
    return (
        commonPrompt(task, draft)
        + "현재 초안의 문장을 고치는 데 매이지 말고 아래 사실 원장을 전부 한 번씩 알맞은 자리에 배치해 새로 "
        "쓴다. F 번호나 원장이라는 말은 결과에 쓰지 않는다. 서로 다른 사실을 합쳐 인과로 바꾸지 않는다.\n\n"
        "<사실 원장>\n"
        + facts
        + "\n</사실 원장>\n\n"
        + f"그대로 보존할 표면: {mustInclude}\n"
        + f"최종 본문은 공백 포함 {minimum}자 이상 {maximum}자 이하다."
    )


def buildManifest(baseManifest: dict, baseResponses: dict, baseAutomatic: dict) -> dict:
    responses = responseMapOf(baseResponses)
    automatic = automaticMapOf(baseAutomatic)
    tasks = []
    for original in baseManifest["tasks"]:
        task = {key: value for key, value in original.items() if key != "prompts"}
        draft = responses[(task["id"], BASELINE)]["output"]
        result = automatic[(task["id"], BASELINE)]
        task["prompts"] = {
            "retryRevision": retryPrompt(task, draft),
            "guardedRepair": guardedPrompt(task, draft, result, False),
            "guardedLintRepair": guardedPrompt(task, draft, result, True),
            "ledgerRewrite": ledgerPrompt(task, draft),
        }
        tasks.append(task)
    payload = {
        "version": 1,
        "baseline": BASELINE,
        "conditions": list(CONDITIONS),
        "baseManifestSha256": baseManifest["contentSha256"],
        "baseResponsesSha256": baseResponses["rawResponseSha256"],
        "baseAutomaticSha256": baseAutomatic["contentSha256"],
        "tasks": tasks,
    }
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def selfTest() -> None:
    task = {
        "id": "x",
        "preset": "blog",
        "briefMarkdown": "# 요구",
        "length": [100, 200],
        "facts": ["값은 3이다."],
        "mustInclude": ["3"],
    }
    automatic = {
        "characterCount": 50,
        "missingLiterals": ["3"],
        "missingNumbers": ["3"],
        "extraNumbers": [],
        "forbiddenHits": [],
    }
    prompt = guardedPrompt(task, "값이 있다.", automatic, False)
    assert "빠진 필수 표면: 3" in prompt and "100자 이상 200자 이하" in prompt


def parseArgs(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="완성 글의 사실 가드 수정 실험")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("baseManifest", type=Path)
    prepare.add_argument("baseResponses", type=Path)
    prepare.add_argument("baseAutomatic", type=Path)
    prepare.add_argument("--output", type=Path, required=True)
    generate = subparsers.add_parser("generate")
    generate.add_argument("manifest", type=Path)
    generate.add_argument("baseResponses", type=Path)
    generate.add_argument("--model", required=True)
    generate.add_argument("--endpoint", default=OLLAMA_ENDPOINT)
    generate.add_argument("--timeout", type=int, default=300)
    generate.add_argument("--output", type=Path, required=True)
    auto = subparsers.add_parser("score-auto")
    auto.add_argument("manifest", type=Path)
    auto.add_argument("responses", type=Path)
    auto.add_argument("--output", type=Path, required=True)
    judge = subparsers.add_parser("judge")
    judge.add_argument("manifest", type=Path)
    judge.add_argument("responses", type=Path)
    judge.add_argument("--model", required=True)
    judge.add_argument("--endpoint", default=OLLAMA_ENDPOINT)
    judge.add_argument("--timeout", type=int, default=300)
    judge.add_argument("--output", type=Path, required=True)
    score = subparsers.add_parser("score")
    score.add_argument("manifest", type=Path)
    score.add_argument("responses", type=Path)
    score.add_argument("automatic", type=Path)
    score.add_argument("judgments", type=Path)
    score.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        selfTest()
        print("writingLift repair self-test 통과")
        return 0
    args = parseArgs(argv)
    if args.command == "prepare":
        manifest = buildManifest(
            readJson(args.baseManifest),
            readJson(args.baseResponses),
            readJson(args.baseAutomatic),
        )
        writeJson(args.output, manifest)
        print(f"repair manifest SHA256: {sha256File(args.output)}")
    elif args.command == "generate":
        runGeneration(
            readJson(args.manifest),
            readJson(args.baseResponses),
            args.model,
            args.endpoint,
            args.timeout,
            args.output,
        )
        print(f"repair responses SHA256: {sha256File(args.output)}")
    elif args.command == "score-auto":
        automatic = scoreAutomatic(readJson(args.manifest), readJson(args.responses))
        writeJson(args.output, automatic)
        print(f"repair automatic SHA256: {sha256File(args.output)}")
    elif args.command == "judge":
        runJudgments(
            readJson(args.manifest),
            readJson(args.responses),
            args.model,
            args.endpoint,
            args.timeout,
            args.output,
        )
        print(f"repair judgments SHA256: {sha256File(args.output)}")
    else:
        score = scoreAll(
            readJson(args.manifest),
            readJson(args.responses),
            readJson(args.automatic),
            readJson(args.judgments),
        )
        writeJson(args.output, score)
        print(renderScore(score))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
