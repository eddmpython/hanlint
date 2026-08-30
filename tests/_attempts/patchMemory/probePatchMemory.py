"""patchMemory. 승인 패치 선택과 기권을 일반 본보기와 같은 과제에서 견준다.

MDN 한국어 문서 Git 이력에서 `hanlint learn`으로 찾고 뜻 보존을 직접 확인한 두 전후 짝만 쓴다. 현재
말뭉치에서 같은 rule, preset, cue, reader가 맞는 과제와 한 조건이 다른 과제를 함께 뽑는다.

```powershell
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/patchMemory/probePatchMemory.py prepare `
  ../hanlint.out/corpus --output manifest.json
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/patchMemory/probePatchMemory.py run manifest.json `
  --ollama-model qwen3:8b --output responses.json
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/patchMemory/probePatchMemory.py judgment-template `
  manifest.json responses.json --output judgments.json
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/patchMemory/probePatchMemory.py score `
  manifest.json responses.json --judgments judgments.json
```
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXEMPLAR_PROBE = ROOT / "tests" / "_attempts" / "exemplarLift"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(EXEMPLAR_PROBE))

from probeExemplarLift import (  # noqa: E402
    OLLAMA_ENDPOINT,
    OLLAMA_OPTIONS,
    applyJudgments,
    contextFor,
    ollamaGenerate,
    ollamaInfo,
    promptFor,
    readJson,
    resultOf,
    taskId,
    writeJson,
)

from hanlint import Config, fingerprint, lintText  # noqa: E402
from hanlint.data import Patch, exemplarFor, projectPatches  # noqa: E402
from hanlint.fingerprint import readerKind  # noqa: E402
from hanlint.report import exemplarInRegister  # noqa: E402

CONDITIONS = ("reasonOnly", "blindExemplar", "selectedPatch")
MATCH_KINDS = ("exact", "readerMismatch", "cueMismatch")

MDN_PATCHES = (
    {
        "rule": "translationese",
        "before": "요소는 toLocaleString 메서드를 사용하여 문자열로 변환되고 이 문자열은 locale 고유 문자열에 의해 분리됩니다.",
        "after": (
            "각 요소는 자체 toLocaleString 메서드를 사용하여 문자열로 변환되며, "
            "이러한 문자열은 로케일별 구분 문자열로 분리됩니다."
        ),
        "moved": "행위의 주체를 문장 앞으로 옮김",
        "cue": "에 의해",
        "reader": "recent",
        "presets": ["docs"],
        "source": {
            "repo": "https://github.com/mdn/translated-content",
            "commit": "742d9a9829df079fc9de3096cfac245344ce1bc3",
            "path": "files/ko/web/javascript/reference/global_objects/array/tolocalestring/index.md",
            "license": "CC-BY-SA-2.5",
        },
    },
    {
        "rule": "spacing",
        "before": "필요할때 최적화하세요.",
        "after": "필요할 때 최적화하세요.",
        "moved": "의존 명사 앞을 띄어 씀",
        "cue": "할때",
        "reader": "new",
        "presets": ["docs"],
        "source": {
            "repo": "https://github.com/mdn/translated-content",
            "commit": "01a8e49f8540454a5a1a8189f5f3d1408166332c",
            "path": "files/ko/web/performance/critical_rendering_path/index.md",
            "license": "CC-BY-SA-2.5",
        },
    },
)

AUTHOR_BLOG_PATCHES = (
    {
        "rule": "fillerOpener",
        "before": "다음으로 코드를 넣을 파일을 만듭니다.",
        "after": "segno 는 이제 깔렸습니다. 그 라이브러리를 부를 파이썬 파일을 만들 차례입니다.",
        "moved": "앞에서 만든 결과를 이름으로 받고 다음 행동을 붙임",
        "cue": "다음으로",
        "reader": "known",
        "presets": ["blog"],
        "context": {
            "before": ["python -m pip 는 지금 이 터미널이 쓰는 파이썬에 설치합니다."],
            "after": ["메모장을 열고 아래를 붙여 넣습니다."],
        },
        "source": {
            "repo": "https://github.com/eddmpython/eddmpython",
            "commit": "8531fdf1c03d9f5a1733d6f769a81ce0ead2d45b",
            "path": "blog/posts/003-python-qr/index.md",
            "license": "MIT",
        },
    },
    {
        "rule": "cliche",
        "before": (
            "핵심은 아래 세 줄 가운데 make_qr 과 save 이고, os 와 print 는 만든 파일이 어디 저장됐는지 "
            "화면에 찍어 주려고 붙인 것입니다."
        ),
        "after": (
            "make_qr.py 에서 QR코드를 실제로 만드는 것은 import segno 와 make_qr 과 save 세 줄이고, "
            "os 와 print 는 만든 파일이 어디 저장됐는지 화면에 찍어 주려고 붙인 것입니다."
        ),
        "moved": "포장하는 말을 지우고 무엇이 핵심인지 주어로 세움",
        "cue": "핵심은",
        "reader": "known",
        "presets": ["blog"],
        "context": {
            "before": [],
            "after": [
                "segno.make_qr 에 넣은 웹 주소가 QR코드로 바뀝니다.",
                "qr.save 는 그 QR코드를 link.png 라는 그림 파일로 저장합니다.",
            ],
        },
        "source": {
            "repo": "https://github.com/eddmpython/eddmpython",
            "commit": "8531fdf1c03d9f5a1733d6f769a81ce0ead2d45b",
            "path": "blog/posts/003-python-qr/index.md",
            "license": "MIT",
        },
    },
    {
        "rule": "danglingDeixis",
        "before": "이것을 오늘 파이썬에 넣으면 이렇게 멈춥니다.",
        "after": "이 Set 클래스를 오늘 파이썬에 넣으면 이렇게 멈춥니다.",
        "moved": "지시어를 앞 문맥에서 확인한 대상 이름으로 바꿈",
        "cue": "이것을",
        "reader": "known",
        "presets": ["blog"],
        "context": {
            "before": [
                "다음은 거기 실린 코드를 줄인 것입니다.",
                "class Set():",
            ],
            "after": ["SyntaxError: cannot assign to subscript here. Maybe you meant '==' instead of '='?"],
        },
        "source": {
            "repo": "https://github.com/eddmpython/eddmpython",
            "commit": "8531fdf1c03d9f5a1733d6f769a81ce0ead2d45b",
            "path": "blog/posts/005-python-history/index.md",
            "license": "MIT",
        },
    },
)

PATCH_SETS = {"mdn": MDN_PATCHES, "authorBlog": AUTHOR_BLOG_PATCHES}


def patchObjects(patchSet: str = "mdn") -> tuple[Patch, ...]:
    entries = [{key: value for key, value in entry.items() if key not in {"context", "source"}} for entry in PATCH_SETS[patchSet]]
    return projectPatches(entries, ("blog", "report", "docs", "guide", "essay", "fiction", "encyclopedia"))


def experimentPatch(patch: Patch, preset: str) -> dict:
    """실험 당시 고정한 표면. 뒤의 제품 메타데이터 추가가 manifest hash를 바꾸지 않게 한다."""
    return {
        "before": patch.before,
        "after": patch.after,
        "moved": patch.moved,
        "match": {"preset": preset, "cue": patch.cue, "reader": patch.reader},
    }


def manifestPatch(patch: Patch, patchSet: str) -> dict:
    source = next(entry["source"] for entry in PATCH_SETS[patchSet] if entry["rule"] == patch.rule)
    return {"rule": patch.rule, **experimentPatch(patch, patch.presets[0]), "source": source}


def matchKind(patch: Patch, cue: str, reader: str) -> str:
    if cue == patch.cue and reader == patch.reader:
        return "exact"
    if cue == patch.cue:
        return "readerMismatch"
    return "cueMismatch"


def corpusEntries(corpus: Path) -> list[dict]:
    metadataPath = corpus / "metadata.json"
    if metadataPath.exists():
        return readJson(metadataPath)["documents"]
    return [
        {
            "path": str(path.relative_to(corpus)),
            "preset": "blog",
            "source": corpus.name,
        }
        for path in sorted(corpus.glob("content/**/index.md"))
    ]


def corpusDescription(corpus: Path) -> dict:
    metadataPath = corpus / "metadata.json"
    entries = corpusEntries(corpus)
    description = {"path": str(corpus), "documents": len(entries)}
    if metadataPath.exists():
        description["metadataSha256"] = hashlib.sha256(metadataPath.read_bytes()).hexdigest()
        return description
    fileDigest = hashlib.sha256()
    for entry in entries:
        path = corpus / entry["path"]
        fileDigest.update(entry["path"].replace("\\", "/").encode())
        fileDigest.update(b"\0")
        fileDigest.update(hashlib.sha256(path.read_bytes()).digest())
    description["filesSha256"] = fileDigest.hexdigest()
    return description


def candidateTasks(corpus: Path, patchSet: str) -> list[dict]:
    patches = patchObjects(patchSet)
    preset = patches[0].presets[0]
    config = Config(preset=preset)
    patchByRule = {patch.rule: patch for patch in patches}
    candidates: list[dict] = []
    seen: set[str] = set()
    for entry in corpusEntries(corpus):
        if entry["preset"] != preset:
            continue
        path = corpus / entry["path"]
        text = path.read_text(encoding="utf-8")
        document = fingerprint(text, config, path=str(path))
        for finding in lintText(text, config, path=str(path)):
            patch = patchByRule.get(finding.rule)
            if patch is None or finding.scope != "sentence" or finding.at < 0:
                continue
            sentence = document.sentences[finding.at].text.strip()
            if not sentence or sentence in (patch.before, patch.after):
                continue
            identifier = taskId(finding.rule, sentence)
            if identifier in seen:
                continue
            seen.add(identifier)
            state = document.reader.beforeSentence[finding.at]
            currentReader = readerKind(document.sentences[finding.at], state)
            kind = matchKind(patch, finding.localCue, currentReader)
            blind = exemplarFor(finding.rule, config.preset, config.exemplars)
            if blind is None:
                continue
            blindData = exemplarInRegister(blind, document.register).asDict()
            selected = patch if kind == "exact" else None
            selectedData = experimentPatch(selected, config.preset) if selected else None
            context = contextFor(document, finding.at)
            candidates.append(
                {
                    "id": identifier,
                    "source": entry["path"],
                    "sourceSet": entry["source"],
                    "rule": finding.rule,
                    "why": finding.why,
                    "sentence": sentence,
                    "context": context,
                    "preset": config.preset,
                    "cue": finding.localCue,
                    "reader": currentReader,
                    "matchKind": kind,
                    "blindExemplar": blindData,
                    "selectedPatch": selectedData,
                }
            )
    return candidates


def prepareManifest(corpus: Path, patchSet: str, perBucket: int, minimumBucket: int) -> dict:
    candidates = candidateTasks(corpus, patchSet)
    selected: list[dict] = []
    buckets = Counter()
    for task in sorted(candidates, key=lambda item: hashlib.sha256(item["id"].encode()).hexdigest()):
        bucket = (task["rule"], task["matchKind"])
        if buckets[bucket] >= perBucket:
            continue
        buckets[bucket] += 1
        reasonPrompt = promptFor(task["sentence"], task["rule"], task["why"], task["context"])
        task["prompts"] = {
            "reasonOnly": reasonPrompt,
            "blindExemplar": promptFor(task["sentence"], task["rule"], task["why"], task["context"], task["blindExemplar"]),
            "selectedPatch": (
                promptFor(task["sentence"], task["rule"], task["why"], task["context"], task["selectedPatch"])
                if task["selectedPatch"]
                else reasonPrompt
            ),
        }
        selected.append(task)
    required = {(patch.rule, kind) for patch in patchObjects(patchSet) for kind in MATCH_KINDS}
    missing = sorted(bucket for bucket in required if buckets[bucket] < minimumBucket)
    if missing:
        shown = ", ".join(f"{rule}/{kind}={buckets[(rule, kind)]}" for rule, kind in missing)
        raise ValueError(f"고정 표본을 못 채웠다: {shown}")
    return {
        "version": 1,
        "experiment": "patchMemory",
        "patchSet": patchSet,
        "corpus": corpusDescription(corpus),
        "selection": {
            "conditions": ["rule", "preset", "cue", "reader"],
            "cueMinimumCharacters": 2,
            "abstainWhen": "조건이 하나라도 다르거나 유일하지 않음",
        },
        "approvedPatches": [manifestPatch(patch, patchSet) for patch in patchObjects(patchSet)],
        "perBucket": perBucket,
        "minimumBucket": minimumBucket,
        "bucketCounts": {f"{rule}/{kind}": buckets[(rule, kind)] for rule, kind in sorted(required)},
        "tasks": selected,
    }


def candidateSummary(corpus: Path, patchSet: str) -> dict:
    counts = Counter((task["rule"], task["matchKind"]) for task in candidateTasks(corpus, patchSet))
    required = {(patch.rule, kind) for patch in patchObjects(patchSet) for kind in MATCH_KINDS}
    return {
        "patchSet": patchSet,
        "bucketCounts": {f"{rule}/{kind}": counts[(rule, kind)] for rule, kind in sorted(required)},
        "total": sum(counts.values()),
    }


def promptsForTask(task: dict) -> dict:
    reasonPrompt = promptFor(task["sentence"], task["rule"], task["why"], task["context"])
    return {
        "reasonOnly": reasonPrompt,
        "blindExemplar": promptFor(task["sentence"], task["rule"], task["why"], task["context"], task["blindExemplar"]),
        "selectedPatch": (
            promptFor(task["sentence"], task["rule"], task["why"], task["context"], task["selectedPatch"])
            if task["selectedPatch"]
            else reasonPrompt
        ),
    }


def exactReplayTask(entry: dict, patch: Patch) -> dict:
    preset = patch.presets[0]
    finding = next(item for item in lintText(patch.before, Config(preset=preset)) if item.rule == patch.rule)
    blind = exemplarFor(patch.rule, preset, ())
    if blind is None:
        raise ValueError(f"내장 본보기가 없다: {patch.rule}")
    task = {
        "id": taskId(patch.rule, "approved:" + patch.before),
        "source": entry["source"]["path"],
        "sourceSet": entry["source"]["repo"],
        "rule": patch.rule,
        "why": finding.why,
        "sentence": patch.before,
        "context": entry["context"],
        "preset": preset,
        "cue": patch.cue,
        "reader": patch.reader,
        "matchKind": "exactReplay",
        "blindExemplar": blind.asDict(),
        "selectedPatch": experimentPatch(patch, preset),
    }
    task["prompts"] = promptsForTask(task)
    return task


def prepareReplayManifest(corpus: Path, patchSet: str, mismatchesPerRule: int) -> dict:
    patches = patchObjects(patchSet)
    entries = {entry["rule"]: entry for entry in PATCH_SETS[patchSet]}
    tasks = [exactReplayTask(entries[patch.rule], patch) for patch in patches]
    mismatchCounts = Counter()
    candidates = sorted(candidateTasks(corpus, patchSet), key=lambda item: hashlib.sha256(item["id"].encode()).hexdigest())
    for task in candidates:
        if mismatchCounts[task["rule"]] >= mismatchesPerRule:
            continue
        patch = next(item for item in patches if item.rule == task["rule"])
        if " ".join(task["sentence"].split()) == " ".join(patch.before.split()):
            continue
        mismatchCounts[task["rule"]] += 1
        task["matchKind"] = "sentenceMismatch"
        task["selectedPatch"] = None
        task["prompts"] = promptsForTask(task)
        tasks.append(task)
    missing = [patch.rule for patch in patches if mismatchCounts[patch.rule] < mismatchesPerRule]
    if missing:
        shown = ", ".join(f"{rule}={mismatchCounts[rule]}" for rule in missing)
        raise ValueError(f"문장 불일치 표본을 못 채웠다: {shown}")
    return {
        "version": 1,
        "experiment": "exactPatchReplay",
        "patchSet": patchSet,
        "corpus": corpusDescription(corpus),
        "selection": {
            "conditions": ["normalizedSentence", "rule", "preset", "cue", "reader"],
            "replayWhen": "정규화한 원문과 나머지 조건이 모두 같고 패치가 유일함",
            "abstainWhen": "원문을 포함한 조건이 하나라도 다르거나 유일하지 않음",
        },
        "approvedPatches": [manifestPatch(patch, patchSet) for patch in patches],
        "mismatchesPerRule": mismatchesPerRule,
        "bucketCounts": {
            "exactReplay": len(patches),
            "sentenceMismatch": sum(mismatchCounts.values()),
        },
        "tasks": tasks,
    }


def runManifest(manifest: dict, model: str, endpoint: str, timeout: int, checkpoint: Path | None) -> dict:
    responses: list[dict] = []
    cache: dict[str, tuple[str, dict, str]] = {}
    runner = {
        "kind": "ollama",
        "endpoint": endpoint,
        "model": ollamaInfo(endpoint, model, timeout),
        "think": False,
        "options": OLLAMA_OPTIONS,
    }
    modelPrompts = {
        prompt
        for task in manifest["tasks"]
        for condition, prompt in task["prompts"].items()
        if not (
            manifest["experiment"] == "exactPatchReplay" and condition == "selectedPatch" and task["matchKind"] == "exactReplay"
        )
    }
    uniquePrompts = len(modelPrompts)
    total = len(manifest["tasks"]) * len(CONDITIONS)
    for task in manifest["tasks"]:
        for condition in CONDITIONS:
            prompt = task["prompts"][condition]
            promptHash = hashlib.sha256(prompt.encode()).hexdigest()
            directReplay = (
                manifest["experiment"] == "exactPatchReplay"
                and condition == "selectedPatch"
                and task["matchKind"] == "exactReplay"
            )
            reused = cache.get(promptHash) if not directReplay else None
            if directReplay:
                output = task["selectedPatch"]["after"]
                item = {
                    "taskId": task["id"],
                    "condition": condition,
                    "output": output,
                    "metrics": {"directReplay": True},
                    "promptSha256": promptHash,
                }
            elif reused:
                output, metrics, reusedFrom = reused
                item = {
                    "taskId": task["id"],
                    "condition": condition,
                    "output": output,
                    "metrics": metrics,
                    "promptSha256": promptHash,
                    "reusedFrom": reusedFrom,
                }
            else:
                output, metrics = ollamaGenerate(prompt, model, endpoint, timeout)
                reusedFrom = f"{task['id']}:{condition}"
                cache[promptHash] = (output, metrics, reusedFrom)
                item = {
                    "taskId": task["id"],
                    "condition": condition,
                    "output": output,
                    "metrics": metrics,
                    "promptSha256": promptHash,
                }
            responses.append(item)
            partial = {
                "version": 1,
                "complete": False,
                "uniquePrompts": uniquePrompts,
                "runner": runner,
                "responses": responses,
            }
            if checkpoint:
                writeJson(checkpoint, partial)
            print(f"응답 {len(responses)}/{total}: {task['id']} {condition}", flush=True)
    return {
        "version": 1,
        "complete": True,
        "uniquePrompts": uniquePrompts,
        "runner": runner,
        "responses": responses,
    }


def judgmentTemplate(manifest: dict, responses: dict) -> dict:
    tasks = {task["id"]: task for task in manifest["tasks"]}
    return {
        "version": 1,
        "instructions": "원문과 문맥에 있던 뜻과 사실을 보존했으면 true다. 규칙 해결 여부는 여기서 보지 않는다.",
        "judgments": [
            {
                "taskId": response["taskId"],
                "condition": response["condition"],
                "sentence": tasks[response["taskId"]]["sentence"],
                "output": response["output"],
                "meaningPreserved": None,
                "note": "",
            }
            for response in responses["responses"]
        ],
    }


def scored(manifest: dict, responses: dict) -> tuple[str, dict]:
    tasks = {task["id"]: task for task in manifest["tasks"]}
    config = Config(preset=manifest["tasks"][0]["preset"])
    results = []
    for response in responses["responses"]:
        task = tasks[response["taskId"]]
        result = resultOf(task, response, config)
        results.append(
            {
                "taskId": task["id"],
                "condition": response["condition"],
                "matchKind": task["matchKind"],
                **result,
            }
        )
    lines = [f"과제 {len(tasks)}개, 모델 호출 {responses['uniquePrompts']}회", "", "조건별"]
    summary = {}
    for condition in CONDITIONS:
        chosen = [result for result in results if result["condition"] == condition]
        values = {
            "tasks": len(chosen),
            "resolved": sum(result["resolved"] for result in chosen),
            "newErrors": sum(result["newErrors"] for result in chosen),
            "meaningPreserved": sum(result["meaningPreserved"] for result in chosen),
            "threeChecks": sum(result["threeChecks"] for result in chosen),
        }
        summary[condition] = values
        lines.append(
            f"  {condition:15} 규칙 해결 {values['resolved']}/{values['tasks']}, 새 error {values['newErrors']}건, "
            f"뜻 보존 {values['meaningPreserved']}/{values['tasks']}, 세 조건 충족 {values['threeChecks']}/{values['tasks']}"
        )
    lines.extend(["", "선택 패치와 일반 본보기 짝 비교"])
    pairSummary = {}
    byKey = {(result["taskId"], result["condition"]): result for result in results}
    matchKinds = sorted({task["matchKind"] for task in tasks.values()})
    for kind in ("all", *matchKinds):
        taskIds = [taskId for taskId, task in tasks.items() if kind == "all" or task["matchKind"] == kind]
        pairs = [(byKey[(taskId, "blindExemplar")], byKey[(taskId, "selectedPatch")]) for taskId in taskIds]
        selectedWins = sum(not blind["threeChecks"] and selected["threeChecks"] for blind, selected in pairs)
        blindWins = sum(blind["threeChecks"] and not selected["threeChecks"] for blind, selected in pairs)
        ties = len(pairs) - selectedWins - blindWins
        pairSummary[kind] = {"selectedWins": selectedWins, "blindWins": blindWins, "ties": ties}
        lines.append(f"  {kind:14} 선택만 성공 {selectedWins}, 일반만 성공 {blindWins}, 같은 결과 {ties}")
    data = {"version": 1, "summary": summary, "pairSummary": pairSummary, "results": results}
    return "\n".join(lines), data


def selfTest() -> None:
    patches = patchObjects("mdn")
    assert len(patches) == 2
    assert patches[0].cue == "에 의해" and patches[1].cue == "할때"
    reason = promptFor("문장입니다.", "spacing", "이유", {"before": [], "after": []})
    shown = promptFor(
        "문장입니다.",
        "spacing",
        "이유",
        {"before": [], "after": []},
        {"before": "전입니다.", "after": "후입니다.", "moved": "바꿈"},
    )
    assert reason != shown
    assert len(patchObjects("authorBlog")) == 3


def parseArgs(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="승인 패치 선택과 기권을 일반 본보기와 견준다")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("corpus", type=Path)
    prepare.add_argument("--patch-set", dest="patchSet", choices=tuple(PATCH_SETS), default="mdn")
    prepare.add_argument("--per-bucket", dest="perBucket", type=int, default=4)
    prepare.add_argument("--minimum-bucket", dest="minimumBucket", type=int, default=2)
    prepare.add_argument("--output", type=Path, required=True)
    replay = subparsers.add_parser("prepare-replay")
    replay.add_argument("corpus", type=Path)
    replay.add_argument("--patch-set", dest="patchSet", choices=("authorBlog",), default="authorBlog")
    replay.add_argument("--mismatches-per-rule", dest="mismatchesPerRule", type=int, default=2)
    replay.add_argument("--output", type=Path, required=True)
    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("corpus", type=Path)
    inspect.add_argument("--patch-set", dest="patchSet", choices=tuple(PATCH_SETS), default="mdn")
    inspect.add_argument("--output", type=Path)
    run = subparsers.add_parser("run")
    run.add_argument("manifest", type=Path)
    run.add_argument("--ollama-model", dest="ollamaModel", required=True)
    run.add_argument("--ollama-endpoint", dest="ollamaEndpoint", default=OLLAMA_ENDPOINT)
    run.add_argument("--timeout", type=int, default=120)
    run.add_argument("--output", type=Path, required=True)
    template = subparsers.add_parser("judgment-template")
    template.add_argument("manifest", type=Path)
    template.add_argument("responses", type=Path)
    template.add_argument("--output", type=Path, required=True)
    score = subparsers.add_parser("score")
    score.add_argument("manifest", type=Path)
    score.add_argument("responses", type=Path)
    score.add_argument("--judgments", type=Path, required=True)
    score.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    selfTest()
    args = parseArgs(argv)
    if args.command == "prepare":
        manifest = prepareManifest(args.corpus, args.patchSet, args.perBucket, args.minimumBucket)
        writeJson(args.output, manifest)
        print(f"과제 {len(manifest['tasks'])}개를 {args.output}에 썼다")
    elif args.command == "prepare-replay":
        manifest = prepareReplayManifest(args.corpus, args.patchSet, args.mismatchesPerRule)
        writeJson(args.output, manifest)
        print(f"정확 재생 과제 {len(manifest['tasks'])}개를 {args.output}에 썼다")
    elif args.command == "inspect":
        summary = candidateSummary(args.corpus, args.patchSet)
        if args.output:
            writeJson(args.output, summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.command == "run":
        manifest = readJson(args.manifest)
        responses = runManifest(manifest, args.ollamaModel, args.ollamaEndpoint, args.timeout, args.output)
        writeJson(args.output, responses)
    elif args.command == "judgment-template":
        writeJson(args.output, judgmentTemplate(readJson(args.manifest), readJson(args.responses)))
        print(f"뜻 보존 판정 틀을 {args.output}에 썼다")
    else:
        manifest = readJson(args.manifest)
        responses = applyJudgments(readJson(args.responses), readJson(args.judgments))
        report, data = scored(manifest, responses)
        print(report)
        if args.output:
            writeJson(args.output, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
