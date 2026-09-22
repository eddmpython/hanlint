"""craftLineOne. 작법서에서 1번 줄 (긴 문장을 두어라) 을 지운 판이 내보낸 판을 이기는가.

craftLift 1, 2회차와 codexCraft 에서 작법서 쪽이 진 이유가 두 가족 모두 1번 줄이었다. 이 탐침은 두 판을 같은
과제로 두 필자 (Codex 와 Claude) 에게 쓰게 하고, 판정은 craftLift 의 `judge` 묶음과 이 파일의 `score` 로 한다.
필자 세션은 과제마다 새 세션이고 훅을 모두 끈다. 전역 훅이 내보낸 작법서를 두 갈래에 똑같이 실으면 noLong 갈래가
1번 줄을 보게 되기 때문이다. 사전 등록과 판정 조건은 probeLineOne_log.md 가 소유한다.

```console
python -X utf8 -B tests/_attempts/craftLineOne/probeLineOne.py write <시험 폴더> --writer codex
python -X utf8 -B tests/_attempts/craftLineOne/probeLineOne.py write <시험 폴더> --writer claude
python -X utf8 -B tests/_attempts/craftLineOne/probeLineOne.py follow <시험 폴더>
python -X utf8 -B tests/_attempts/craftLift/probeCraftLift.py judge <시험 폴더>/<필자> --output-dir <시험 폴더>/<필자>/judge \
    --arms shipped,noLong
python -X utf8 -B tests/_attempts/craftLineOne/probeLineOne.py gptJudge <시험 폴더>/<필자>/judge --output-dir <답 폴더>
python -X utf8 -B tests/_attempts/craftLineOne/probeLineOne.py score <시험 폴더> --judgments claudeJudgments
```
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "craftLift"))

from probeCraftLift import arms as readArms  # noqa: E402
from probeCraftLift import measure, signTest  # noqa: E402

GUIDES = {
    "shipped": REPO / "src" / "hanlint" / "data" / "koreanProse.txt",
    "noLong": HERE / "noLongLine.txt",
}
"""갈래 둘. shipped 는 제품이 싣는 본문, noLong 은 1번 절을 지우고 번호와 자기 참조만 맞춘 판이다."""
ARMS = tuple(GUIDES)
WRITERS = ("codex", "claude")
TASKS = HERE / "tasks.json"
TOOL_RULE = "도구를 쓰지 않는다. 파일을 읽거나 명령을 실행하지 않고 바로 답한다."
TASK = "주제: {topic}\n\n이 주제로 한국어 산문 한 편을 500자 안팎으로 쓴다. 제목 없이 본문만 낸다."
"""codexCraft 와 같은 문구다."""
CLAUDE_MODEL = "opus"
CLAUDE_EFFORT = "xhigh"
"""이 기계의 Claude Code 사용자 설정과 같은 모델 계열과 강도. 사용자 설정은 훅 때문에 싣지 않으므로 명시한다."""
TIMEOUT = 900


def prompt(arm: str, topic: str) -> str:
    """두 갈래 모두 작법서를 먼저 읽힌다. 다른 것은 작법서 본문뿐이다."""
    guide = GUIDES[arm].read_text(encoding="utf-8").strip()
    return f"{guide}\n\n---\n\n{TOOL_RULE}\n\n{TASK.format(topic=topic)}"


def executable(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"{name} 을 PATH 에서 찾지 못했다")
    return found


def runWriter(writer: str, text: str, outFile: Path) -> bool:
    """새 세션 하나. 훅을 끄고 마지막 답만 outFile 에 쓴다. 비었거나 실패하면 False."""
    outFile.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="craftLineOne-") as cwd:
        if writer == "codex":
            command = [executable("codex"), "exec", "--skip-git-repo-check", "--ephemeral", "--disable", "hooks"]
            command += ["-s", "read-only", "-C", cwd, "-o", str(outFile), "-"]
        else:
            command = [executable("claude"), "-p", "--setting-sources", "project,local", "--no-session-persistence"]
            command += ["--model", CLAUDE_MODEL, "--effort", CLAUDE_EFFORT]
        try:
            done = subprocess.run(command, input=text.encode("utf-8"), capture_output=True, cwd=cwd, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            return False
    if writer == "claude" and done.returncode == 0:
        outFile.write_text(done.stdout.decode("utf-8").strip() + "\n", encoding="utf-8")
    if done.returncode != 0 or not outFile.exists() or not outFile.read_text(encoding="utf-8").strip():
        outFile.unlink(missing_ok=True)
        return False
    return True


def version(writer: str) -> str:
    done = subprocess.run([executable(writer), "--version"], capture_output=True, text=True, encoding="utf-8")
    return done.stdout.strip()


def meta(root: Path, writer: str) -> None:
    """필자 조건과 두 작법서의 해시."""
    data: dict[str, object] = {"writer": writer, "version": version(writer)}
    if writer == "codex":
        import tomllib

        config = tomllib.loads((Path.home() / ".codex" / "config.toml").read_text(encoding="utf-8"))
        data |= {"model": config.get("model"), "effort": config.get("model_reasoning_effort"), "hooks": "disabled"}
    else:
        data |= {"model": CLAUDE_MODEL, "effort": CLAUDE_EFFORT, "settingSources": "project,local (훅 없음)"}
    data["guides"] = {arm: hashlib.sha256(path.read_bytes()).hexdigest()[:16] for arm, path in GUIDES.items()}
    root.mkdir(parents=True, exist_ok=True)
    (root / "meta.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write(root: Path, writer: str, workers: int, limit: int | None) -> str:
    """없는 글만 쓴다. 끊겨도 다시 돌리면 이어서 쓴다."""
    tasks = json.loads(TASKS.read_text(encoding="utf-8"))
    names = sorted(tasks)[:limit] if limit else sorted(tasks)
    home = root / writer
    meta(home, writer)
    jobs = [(arm, name) for name in names for arm in ARMS if not (home / arm / f"{name}.md").exists()]

    def one(job: tuple[str, str]) -> bool:
        arm, name = job
        outFile = home / arm / f"{name}.md"
        return runWriter(writer, prompt(arm, tasks[name]), outFile) or runWriter(writer, prompt(arm, tasks[name]), outFile)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, jobs))
    failed = [f"{arm}/{name}" for (arm, name), ok in zip(jobs, results, strict=True) if not ok]
    detail = f" ({', '.join(failed)})" if failed else ""
    return f"{writer}: 새로 쓴 글 {len(jobs) - len(failed)}편, 실패 {len(failed)}편{detail}"


def follow(root: Path) -> str:
    """부 지표. 필자와 갈래마다 표지 비율, 긴 문장 비율, 길이 평균과 고름."""
    lines = []
    for writer in WRITERS:
        if not (root / writer).exists():
            continue
        found = readArms(root / writer, ARMS)
        measured = {arm: measure(texts) for arm, texts in found.items()}
        lines.append(f"## {writer}  과제 {measured[ARMS[0]]['글']}개")
        lines.append(f"{'지표':<20}" + "".join(f"{arm:>12}" for arm in ARMS))
        for name in measured[ARMS[0]]["표지"]:
            lines.append(f"{name:<20}" + "".join(f"{measured[arm]['표지'][name]:>12.2f}" for arm in ARMS))
        lines.append(f"{'긴 문장 비율':<20}" + "".join(f"{measured[arm]['긴 문장']:>12.1%}" for arm in ARMS))
        lines.append(f"{'길이 평균 (어절)':<20}" + "".join(f"{measured[arm]['길이 평균']:>12.2f}" for arm in ARMS))
        lines.append(f"{'길이 고름':<20}" + "".join(f"{measured[arm]['길이 고름']:>12.2f}" for arm in ARMS))
        lines.append(f"{'문장':<20}" + "".join(f"{measured[arm]['문장']:>12,}" for arm in ARMS))
        lines.append("")
    return "\n".join(lines)


def verdicts(writerRoot: Path, judgments: str) -> dict[str, str]:
    """{과제: 이긴 갈래 또는 same}. 묶음의 A/B 차례를 order.json 으로 되돌린다."""
    orders = json.loads((writerRoot / "judge" / "order.json").read_text(encoding="utf-8"))["orders"]
    order = {one["taskId"]: one["order"] for one in orders}
    found: dict[str, str] = {}
    for path in sorted((writerRoot / judgments).glob("judge-*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            best = item["best"]
            found[item["taskId"]] = best if best == "same" else order[item["taskId"]]["AB".index(best)]
    return found


def tallyLine(label: str, tally: Counter[str]) -> str:
    total = sum(tally.values())
    a, b = tally[ARMS[1]], tally[ARMS[0]]
    diff = (a - b) / total * 100 if total else 0.0
    return f"{label}: {ARMS[1]} {a}, {ARMS[0]} {b}, same {tally['same']} (차 {diff:+.1f}%p, 부호검정 p {signTest(a, b):.4f})"


def score(root: Path, judgments: str) -> str:
    """필자마다와 합친 수. 판정은 합친 수와 필자마다의 방향으로 한다 (사전 등록)."""
    pooled: Counter[str] = Counter()
    lines = []
    for writer in WRITERS:
        if not (root / writer / judgments).exists():
            continue
        tally = Counter(verdicts(root / writer, judgments).values())
        pooled += tally
        lines.append(tallyLine(writer, tally))
    lines.append(tallyLine("합침", pooled))
    return "\n".join(lines)


def answerArray(text: str) -> list:
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        raise ValueError("JSON 배열이 없다")
    value = json.loads(text[start : end + 1])
    if not isinstance(value, list):
        raise ValueError("배열이 아니다")
    return value


def gptJudge(batchDir: Path, outDir: Path, workers: int) -> str:
    """같은 묶음을 Codex 에게 준다. 심판 세션도 훅을 끈다. 전역 훅이 작법서를 실으면 가림이 깨진다."""
    outDir.mkdir(parents=True, exist_ok=True)
    batches = [p for p in sorted(batchDir.glob("judge-*.md")) if not (outDir / f"{p.stem}.json").exists()]

    def one(batch: Path) -> bool:
        raw = outDir / f"{batch.stem}.txt"
        text = f"{TOOL_RULE}\n\n{batch.read_text(encoding='utf-8')}"
        for _ in range(2):
            if runWriter("codex", text, raw):
                try:
                    items = answerArray(raw.read_text(encoding="utf-8"))
                except ValueError:
                    continue
                (outDir / f"{batch.stem}.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), "utf-8")
                return True
        return False

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, batches))
    return f"묶음 {sum(results)}개 판정, 실패 {len(results) - sum(results)}개"


HUMAN_SEED = 20260922
HUMAN_SPLIT = (24, 6)
"""사람 판정 30쌍. 두 심판이 갈린 쌍에서 24, 같았던 쌍에서 6 (사전 등록)."""
SHEET = HERE / "humanSheet.html"


def humanSheet(root: Path, outDir: Path) -> str:
    """Claude 필자 쌍에서 사람 판정지와 가림 풀이표를 만든다. 풀이표는 판정지에 싣지 않는다."""
    import random

    writerRoot = root / "claude"
    tasks = json.loads(TASKS.read_text(encoding="utf-8"))
    primary, secondary = verdicts(writerRoot, "claudeJudgments"), verdicts(writerRoot, "gptJudgments")
    split = sorted(t for t in primary if primary[t] != secondary[t])
    same = sorted(t for t in primary if primary[t] == secondary[t])
    rng = random.Random(HUMAN_SEED)
    chosen = [(t, "split") for t in rng.sample(split, HUMAN_SPLIT[0])]
    chosen += [(t, "same") for t in rng.sample(same, HUMAN_SPLIT[1])]
    rng.shuffle(chosen)
    found = readArms(writerRoot, ARMS)
    pairs, key = [], {}
    for index, (taskId, stratum) in enumerate(chosen, start=1):
        order = [ARMS[0], ARMS[1]]
        rng.shuffle(order)
        pairId = f"p{index:02d}"
        pairs.append({"id": pairId, "topic": tasks[taskId], "a": found[order[0]][taskId], "b": found[order[1]][taskId]})
        key[pairId] = {"taskId": taskId, "stratum": stratum, "A": order[0], "B": order[1]}
    data = json.dumps(pairs, ensure_ascii=False).replace("</", "<\\/")
    outDir.mkdir(parents=True, exist_ok=True)
    (outDir / "humanSheet.html").write_text(SHEET.read_text(encoding="utf-8").replace("/*PAIRS*/", data), "utf-8")
    (outDir / "key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = f"갈린 쌍 {len(split)}개에서 {HUMAN_SPLIT[0]}, 같았던 쌍 {len(same)}개에서 {HUMAN_SPLIT[1]}"
    return f"{outDir} 에 판정지와 풀이표를 썼다. {counts}"


def humanScore(root: Path, keyFile: Path, verdictFile: Path) -> str:
    """사람 판정을 두 심판과 견준다. verdictFile 은 {짝: {choice}} 이다 (판정지의 verdicts 모음)."""
    writerRoot = root / "claude"
    key = json.loads(keyFile.read_text(encoding="utf-8"))
    human = json.loads(verdictFile.read_text(encoding="utf-8"))
    primary, secondary = verdicts(writerRoot, "claudeJudgments"), verdicts(writerRoot, "gptJudgments")
    agree: Counter[str] = Counter()
    prefer: Counter[str] = Counter()
    decided = 0
    for pairId, row in key.items():
        choice = (human.get(pairId) or {}).get("choice")
        if choice not in ("A", "B", "same"):
            continue
        decided += 1
        arm = "same" if choice == "same" else row[choice]
        prefer[arm] += 1
        if row["stratum"] == "split" and arm != "same":
            agree["claude" if primary[row["taskId"]] == arm else "codex" if secondary[row["taskId"]] == arm else "neither"] += 1
        if row["stratum"] == "same":
            agree["both" if primary[row["taskId"]] == arm else "neither"] += 1
    lines = [f"판정한 쌍 {decided}/{len(key)}"]
    lines.append(
        f"갈린 쌍: 사람이 Claude 심판과 {agree['claude']}, Codex 심판과 {agree['codex']} "
        f"(부호검정 p {signTest(agree['claude'], agree['codex']):.4f})"
    )
    lines.append(f"같았던 쌍: 두 심판과 같음 {agree['both']}, 다름 {agree['neither']}")
    lines.append(
        f"사람 선호 (표본이 갈린 쌍으로 기울었다): noLong {prefer['noLong']}, shipped {prefer['shipped']}, "
        f"비슷하다 {prefer['same']}"
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("write")
    one.add_argument("root", type=Path)
    one.add_argument("--writer", choices=WRITERS, required=True)
    one.add_argument("--workers", type=int, default=4)
    one.add_argument("--limit", type=int, help="과제 이름 순서로 앞의 몇 개만. 시범 실행용")
    two = sub.add_parser("follow")
    two.add_argument("root", type=Path)
    three = sub.add_parser("gptJudge")
    three.add_argument("batchDir", type=Path)
    three.add_argument("--output-dir", dest="outputDir", type=Path, required=True)
    three.add_argument("--workers", type=int, default=4)
    four = sub.add_parser("score")
    four.add_argument("root", type=Path)
    four.add_argument("--judgments", default="claudeJudgments", help="필자 폴더 안의 답 폴더 이름")
    five = sub.add_parser("prompt", help="갈래 하나의 프롬프트를 그대로 찍는다")
    five.add_argument("arm", choices=ARMS)
    five.add_argument("taskId")
    six = sub.add_parser("humanSheet", help="사람 판정지와 가림 풀이표를 만든다")
    six.add_argument("root", type=Path)
    six.add_argument("--output-dir", dest="outputDir", type=Path, required=True)
    seven = sub.add_parser("humanScore", help="사람 판정을 두 심판과 견준다")
    seven.add_argument("root", type=Path)
    seven.add_argument("--key", type=Path, required=True)
    seven.add_argument("--verdicts", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "humanSheet":
        print(humanSheet(args.root, args.outputDir))
        return
    if args.command == "humanScore":
        print(humanScore(args.root, args.key, args.verdicts))
        return
    if args.command == "write":
        print(write(args.root, args.writer, args.workers, args.limit))
    elif args.command == "follow":
        print(follow(args.root))
    elif args.command == "gptJudge":
        print(gptJudge(args.batchDir, args.outputDir, args.workers))
    elif args.command == "score":
        print(score(args.root, args.judgments))
    else:
        tasks = json.loads(TASKS.read_text(encoding="utf-8"))
        print(prompt(args.arm, tasks[args.taskId]))


if __name__ == "__main__":
    main()
