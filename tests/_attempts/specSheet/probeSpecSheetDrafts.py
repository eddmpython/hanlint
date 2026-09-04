"""숫자 사양, primer, 추가 자료 없음의 첫 초안 18편을 같은 요구로 견준다.

제품 코드를 바꾸는 탐침이 아니다. 배포된 spec과 primer를 그대로 읽혀 qwen3:8b가 쓴 첫 초안의 Finding,
요구 분량, spec 열 줄 준수를 센다. 응답 전문은 저장소 밖 --output에 체크포인트로 두고 저장소에는 집계와
SHA-256만 남긴다.

uv run python -X utf8 -B tests/_attempts/specSheet/probeSpecSheetDrafts.py run `
  --model qwen3:8b `
  --output C:/Users/MSI/AppData/Local/dev-workspace/hanlint-specSheet-round2/responses.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import urllib.request
from hashlib import sha256
from math import ceil, floor
from pathlib import Path

from hanlint import Config, fingerprint, lintText
from hanlint.cli.commands.primer import primerEntries, renderPrimer
from hanlint.config import PROFILE_OF, numberValues
from hanlint.data.profiles import profileOf
from hanlint.profile.build import endingRunsOf, sentenceValues
from hanlint.report import renderWritingSpec, writingSpec

REPO = Path(__file__).resolve().parents[3]
CONDITIONS = ("spec", "primer", "plain")
SEEDS = (42, 43)
OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
GENERATION_OPTIONS = {"temperature": 0, "num_predict": 1200}
CHARS_PER_WORD = 6
SPEC_ROW_IDS = (
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
)

TASKS = (
    {
        "id": "blog",
        "preset": "blog",
        "register": "합니다",
        "targetChars": 750,
        "minChars": 600,
        "maxChars": 900,
        "factText": "Polars로 엑셀 파일 12개를 합친다. 입력은 files/*.xlsx이고 결과 파일은 통합.xlsx다.",
        "requiredSurface": ("Polars", "files/*.xlsx", "통합.xlsx", "12"),
        "requirement": (
            "Polars로 엑셀 파일 12개를 합치는 블로그 글을 쓴다. 독자는 파이썬을 처음 쓰는 사무직이다. "
            "입력은 files/*.xlsx이고 결과 파일은 통합.xlsx다. 설치, 파일 찾기, 합치기, 저장, 확인 순서를 설명한다. "
            "합니다체와 Markdown을 쓰고 공백 포함 600자 이상 900자 이하로 쓴다."
        ),
    },
    {
        "id": "docs",
        "preset": "docs",
        "register": "한다",
        "targetChars": 650,
        "minChars": 500,
        "maxChars": 800,
        "factText": "설정 파일은 tablecheck.toml이다. 키는 input, required, onMissing이며 값은 warn 또는 error다.",
        "requiredSurface": ("tablecheck.toml", "input", "required", "onMissing", "warn", "error"),
        "requirement": (
            "가상 명령줄 도구 tablecheck의 설정 파일 형식을 정의하는 참고 문서를 쓴다. 파일 이름은 "
            "tablecheck.toml이다. 키는 input, required, onMissing 세 개뿐이다. onMissing은 warn 또는 error이며 "
            "기본값은 warn이다. 한다체와 Markdown을 쓰고 공백 포함 500자 이상 800자 이하로 쓴다."
        ),
    },
    {
        "id": "report",
        "preset": "report",
        "register": "한다",
        "targetChars": 650,
        "minChars": 500,
        "maxChars": 800,
        "factText": (
            "2026년 8월 14일 09:20부터 10:05까지 작업 37건이 실패했다. 인증 토큰을 30일 주기로 교체한다. 담당은 플랫폼 팀이다."
        ),
        "requiredSurface": ("2026", "8월 14일", "09:20", "10:05", "37", "30일", "플랫폼 팀"),
        "requirement": (
            "2026년 8월 파이프라인 장애 보고서를 쓴다. 장애는 8월 14일 09:20부터 10:05까지 이어졌고 "
            "작업 37건이 실패했다. 원인은 만료된 인증 토큰이다. 재발 방지는 30일 주기 교체이며 담당은 플랫폼 팀이다. "
            "한다체와 Markdown을 쓰고 공백 포함 500자 이상 800자 이하로 쓴다."
        ),
    },
)


def stableJson(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256Text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def writeJson(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def readJson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ollamaJson(endpoint: str, route: str, timeout: int, data: dict | None = None) -> dict:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    request = urllib.request.Request(
        endpoint.rstrip("/") + route,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def modelInfo(endpoint: str, model: str, timeout: int) -> dict:
    tags = ollamaJson(endpoint, "/api/tags", timeout)
    found = next((item for item in tags.get("models", []) if item.get("name") == model), None)
    if found is None:
        raise RuntimeError(f"Ollama에 {model} 모델이 없다")
    return {key: found[key] for key in ("name", "digest", "size", "modified_at") if key in found}


def generate(prompt: str, model: str, endpoint: str, timeout: int, seed: int) -> tuple[str, dict]:
    options = {**GENERATION_OPTIONS, "seed": seed}
    result = ollamaJson(
        endpoint,
        "/api/generate",
        timeout,
        {"model": model, "prompt": prompt, "stream": False, "think": False, "keep_alive": "10m", "options": options},
    )
    output = result.get("response", "").strip()
    metrics = {
        key: result[key]
        for key in ("done_reason", "total_duration", "load_duration", "prompt_eval_count", "eval_count")
        if key in result
    }
    return output, metrics


def assets() -> dict[tuple[str, str], str]:
    found = {}
    for task in TASKS:
        config = Config(preset=task["preset"])
        key = task["id"]
        found[(key, "spec")] = renderWritingSpec(writingSpec(config, task["register"], task["targetChars"]))
        found[(key, "primer")] = renderPrimer(primerEntries(config, task["register"]), task["preset"], task["register"])
        found[(key, "plain")] = "추가 작법 자료 없음"
    return found


def promptFor(task: dict, condition: str, source: str) -> str:
    return f"""아래 요구에 맞는 첫 초안을 작성하십시오.

요구:
{task["requirement"]}

조건 자료:
{source}

조건 자료는 문장 형식만 안내합니다. 그 안의 예시, 수치, 파일 이름을 결과의 사실로 옮기지 마십시오.
요구에 적힌 사실만 쓰고 결과 글만 Markdown으로 출력하십시오. 작성 과정이나 자기 평가는 쓰지 마십시오.
hanlint나 다른 검사기를 실행하지 마십시오."""


def revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


def design(sourceByKey: dict[tuple[str, str], str]) -> dict:
    promptTasks = tuple(
        {key: value for key, value in task.items() if key not in ("factText", "requiredSurface")} for task in TASKS
    )
    material = {
        "tasks": promptTasks,
        "conditions": CONDITIONS,
        "seeds": SEEDS,
        "generationOptions": GENERATION_OPTIONS,
        "assets": {f"{taskId}/{condition}": sha256Text(text) for (taskId, condition), text in sourceByKey.items()},
    }
    return {**material, "sha256": sha256Text(stableJson(material))}


def responseKey(item: dict) -> tuple[str, str, int]:
    return item["taskId"], item["condition"], item["repetition"]


def loadCheckpoint(path: Path, designData: dict, runner: dict) -> dict:
    if not path.exists():
        return {
            "version": 1,
            "complete": False,
            "repositoryRevision": revision(),
            "designSha256": designData["sha256"],
            "runner": runner,
            "responses": [],
        }
    value = readJson(path)
    if value.get("designSha256") != designData["sha256"]:
        raise ValueError("기존 응답의 실험 설계가 현재 코드와 다르다")
    if value.get("runner", {}).get("model", {}).get("digest") != runner["model"].get("digest"):
        raise ValueError("기존 응답의 모델 digest가 현재 모델과 다르다")
    return value


def observedPercentile(values: list[int], level: int) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, ceil(len(ordered) * level / 100) - 1)]


def nearest(value: float) -> int:
    return floor(value + 0.5)


def draftText(output: str) -> tuple[str, bool]:
    """응답 전체를 감싼 markdown 펜스만 벗긴다. TOML이나 닫히지 않은 펜스는 결과 실패 그대로 둔다."""
    lines = output.splitlines()
    if len(lines) >= 2 and lines[0].strip().casefold() == "```markdown" and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip(), True
    return output, False


def specChecks(text: str, task: dict, config: Config) -> dict[str, bool]:
    document = fingerprint(text, config, task["id"] + ".md")
    kind = PROFILE_OF[task["preset"]]
    profile = profileOf(kind) if kind else None
    if profile is None:
        raise ValueError(f"{task['preset']} 프로파일이 없다")
    sentences = list(document.sentences)
    featureValues = sentenceValues(document)
    sentenceCount = len(sentences)
    paragraphCounts = [paragraph.sentenceCount for paragraph in document.paragraphs]
    paragraphP50 = profile.paragraph["sentenceCount"].percentile(50)
    paragraphP90 = profile.paragraph["sentenceCount"].percentile(90)
    lengthP50 = profile.sentence["length"].percentile(50)
    expectedSentences = max(1, nearest(task["targetChars"] / CHARS_PER_WORD / lengthP50))
    expectedParagraphs = max(1, nearest(expectedSentences / paragraphP50))

    def values(name: str) -> list[int]:
        return featureValues[name]

    def distributionAtMost(name: str) -> bool:
        seen = values(name)
        reference = profile.sentence[name]
        return observedPercentile(seen, 50) <= reference.percentile(50) and observedPercentile(seen, 90) <= reference.percentile(
            90
        )

    lengths = values("length")
    runValues = endingRunsOf(document)
    connectorRate = sum(sentence.connectorStart is not None for sentence in sentences) / sentenceCount if sentenceCount else 0
    questionRate = document.questionCount / sentenceCount if sentenceCount else 0
    lengthOk = distributionAtMost("length")
    if config.enabled("longSentence"):
        lengthOk = lengthOk and max(lengths, default=0) <= config.longSentenceMax
    endingOk = observedPercentile(runValues, 50) <= profile.endingRuns.percentile(50) and observedPercentile(
        runValues, 90
    ) <= profile.endingRuns.percentile(90)
    if config.enabled("endingRepeat"):
        endingOk = endingOk and not any(finding.rule == "endingRepeat" for finding in lintText(text, config))
    euiOk = distributionAtMost("euiCount")
    if config.enabled("euiChain"):
        euiOk = euiOk and not any(finding.rule == "euiChain" for finding in lintText(text, config))
    nounOk = observedPercentile(values("nounRun"), 90) <= profile.sentence["nounRun"].percentile(90)
    if config.enabled("nounPile"):
        nounOk = nounOk and not any(finding.rule == "nounPile" for finding in lintText(text, config))
    if config.enabled("noQuestion"):
        questionOk = len(document.bodySections) < 2 or document.questionCount >= 1
    else:
        questionOk = questionRate <= profile.rates["question"]["p90"]
    return {
        "amount": len(document.paragraphs) == expectedParagraphs
        and bool(paragraphCounts)
        and all(paragraphP50 <= count <= paragraphP90 for count in paragraphCounts),
        "sentenceLength": lengthOk,
        "endingRun": endingOk,
        "commas": observedPercentile(values("commas"), 50) <= profile.sentence["commas"].percentile(50)
        and observedPercentile(values("commas"), 90) <= profile.sentence["commas"].percentile(90)
        and observedPercentile(values("commas"), 99) <= profile.sentence["commas"].percentile(99),
        "euiCount": euiOk,
        "nounRun": nounOk,
        "newTopics": distributionAtMost("newTopics"),
        "connector": connectorRate <= profile.rates["connector"]["p90"],
        "numbers": distributionAtMost("numbers"),
        "question": questionOk,
    }


def measure(item: dict) -> dict:
    task = next(task for task in TASKS if task["id"] == item["taskId"])
    config = Config(preset=task["preset"])
    text, outerMarkdownFence = draftText(item["output"])
    findings = lintText(text, config, task["id"] + ".md")
    document = fingerprint(text, config)
    requiredSurfaceOk = all(value in text for value in task["requiredSurface"])
    expectedNumbers = set(numberValues(task["factText"]))
    actualNumbers = set(numberValues(text))
    missingNumbers = sorted(expectedNumbers - actualNumbers)
    unexpectedNumbers = sorted(actualNumbers - expectedNumbers)
    complete = item["metrics"].get("done_reason") != "length"
    draftValid = complete and bool(document.sentences) and requiredSurfaceOk
    checks = specChecks(text, task, config) if draftValid else dict.fromkeys(SPEC_ROW_IDS, False)
    return {
        "chars": len(text),
        "lengthViolation": not task["minChars"] <= len(text) <= task["maxChars"],
        "outerMarkdownFence": outerMarkdownFence,
        "complete": complete,
        "requiredSurfaceOk": requiredSurfaceOk,
        "draftValid": draftValid,
        "missingNumbers": missingNumbers,
        "unexpectedNumbers": unexpectedNumbers,
        "register": document.register,
        "registerOk": document.register == task["register"],
        "errors": sum(finding.severity == "error" for finding in findings),
        "notices": sum(finding.severity == "notice" for finding in findings),
        "rules": [finding.rule for finding in findings],
        "specChecks": checks,
        "specPassed": sum(checks.values()),
        "specTotal": len(checks),
    }


def summarize(checkpoint: dict) -> dict:
    measured = [{**item, "measurement": measure(item)} for item in checkpoint["responses"]]
    byCondition = {}
    for condition in CONDITIONS:
        items = [item["measurement"] for item in measured if item["condition"] == condition]
        byCondition[condition] = {
            "drafts": len(items),
            "errors": sum(item["errors"] for item in items),
            "errorDrafts": sum(item["errors"] > 0 for item in items),
            "notices": sum(item["notices"] for item in items),
            "invalidDrafts": sum(not item["draftValid"] for item in items),
            "numberViolations": sum(len(item["missingNumbers"]) + len(item["unexpectedNumbers"]) for item in items),
            "lengthViolations": sum(item["lengthViolation"] for item in items),
            "registerOk": sum(item["registerOk"] for item in items),
            "specPassed": sum(item["specPassed"] for item in items),
            "specTotal": sum(item["specTotal"] for item in items),
        }
    spec = byCondition["spec"]
    rivals = [byCondition["primer"], byCondition["plain"]]
    adopt = (
        spec["errors"] <= min(item["errors"] for item in rivals)
        and spec["notices"] <= byCondition["plain"]["notices"]
        and spec["lengthViolations"] <= min(item["lengthViolations"] for item in rivals)
        and all(spec["specPassed"] * item["specTotal"] > item["specPassed"] * spec["specTotal"] for item in rivals)
    )
    rows = {}
    for condition in CONDITIONS:
        rows[condition] = {
            row: sum(item["measurement"]["specChecks"][row] for item in measured if item["condition"] == condition)
            for row in next(iter(measured))["measurement"]["specChecks"]
        }
    return {
        "byCondition": byCondition,
        "rowPassesOutOfSix": rows,
        "adoptionRule": (
            "spec의 error가 두 조건 이하, notice가 plain 이하, 분량 위반이 두 조건 이하이고 "
            "사양 준수율이 두 조건보다 모두 높을 때만 기본 절차에 넣는다"
        ),
        "adoptSpecByDefault": adopt,
        "responses": [
            {
                "taskId": item["taskId"],
                "condition": item["condition"],
                "repetition": item["repetition"],
                "outputSha256": item["outputSha256"],
                "measurement": item["measurement"],
            }
            for item in measured
        ],
    }


def run(args: argparse.Namespace) -> int:
    output = args.output.resolve()
    try:
        output.relative_to(REPO.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("응답 전문은 저장소 밖 --output에 둔다")
    sourceByKey = assets()
    designData = design(sourceByKey)
    info = modelInfo(args.endpoint, args.model, args.timeout)
    runner = {"kind": "ollama", "model": info, "think": False, "generationOptions": GENERATION_OPTIONS}
    checkpoint = loadCheckpoint(output, designData, runner)
    seen = {responseKey(item) for item in checkpoint["responses"]}
    schedule = []
    for repetition, seed in enumerate(SEEDS, start=1):
        for taskIndex, task in enumerate(TASKS):
            rotated = (
                CONDITIONS[(taskIndex + repetition - 1) % len(CONDITIONS) :]
                + CONDITIONS[: (taskIndex + repetition - 1) % len(CONDITIONS)]
            )
            schedule.extend((task, condition, repetition, seed) for condition in rotated)
    for task, condition, repetition, seed in schedule:
        key = (task["id"], condition, repetition)
        if key in seen:
            continue
        prompt = promptFor(task, condition, sourceByKey[(task["id"], condition)])
        outputText, metrics = generate(prompt, args.model, args.endpoint, args.timeout, seed)
        checkpoint["responses"].append(
            {
                "taskId": task["id"],
                "condition": condition,
                "repetition": repetition,
                "seed": seed,
                "promptSha256": sha256Text(prompt),
                "output": outputText,
                "outputSha256": sha256Text(outputText),
                "metrics": metrics,
            }
        )
        seen.add(key)
        writeJson(output, checkpoint)
        print(f"초안 {len(seen)}/{len(schedule)}: {task['id']} {condition} {repetition}회", flush=True)
    checkpoint["complete"] = True
    checkpoint["summary"] = summarize(checkpoint)
    writeJson(output, checkpoint)
    print(json.dumps(checkpoint["summary"], ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    runParser = subparsers.add_parser("run")
    runParser.add_argument("--model", default="qwen3:8b")
    runParser.add_argument("--endpoint", default=OLLAMA_ENDPOINT)
    runParser.add_argument("--timeout", type=int, default=300)
    runParser.add_argument("--output", type=Path, required=True)
    runParser.set_defaults(run=run)
    args = parser.parse_args()
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
