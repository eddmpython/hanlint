"""codexCraft. craftLift 를 GPT 필자로 다시 잰다. 작법서가 Codex 가 쓰는 한국어도 낫게 하는가.

craftLift 의 필자와 심판은 claude-opus-5 였다. 이 탐침은 필자만 Codex (`codex exec`) 로 바꾸고 나머지는
craftLift 의 `follow`, `judge`, `score` 를 그대로 쓴다. 작법서는 제품이 싣는 본문 (`src/hanlint/data/koreanProse.txt`)
이고, craftLift 처럼 과제 앞에 붙여 읽힌다. 과제마다 새 세션 (`--ephemeral`) 이다.

사전 등록과 판정 조건은 probeCodexCraft_log.md 가 소유한다. 쓴 글은 저장소 밖에 둔다.

```console
python -X utf8 -B tests/_attempts/codexCraft/probeCodexCraft.py write <시험 폴더>
python -X utf8 -B tests/_attempts/craftLift/probeCraftLift.py follow <시험 폴더>
python -X utf8 -B tests/_attempts/craftLift/probeCraftLift.py judge <시험 폴더> --output-dir <묶음 폴더>
python -X utf8 -B tests/_attempts/codexCraft/probeCodexCraft.py gptJudge <묶음 폴더> --output-dir <답 폴더>
python -X utf8 -B tests/_attempts/craftLift/probeCraftLift.py score <시험 폴더> --judgments <답 폴더> \
    --orders <묶음 폴더>/order.json
```
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GUIDE = REPO / "src" / "hanlint" / "data" / "koreanProse.txt"
TASKS = HERE / "tasks.json"
ARMS = ("plain", "craft")

TOOL_RULE = "도구를 쓰지 않는다. 파일을 읽거나 명령을 실행하지 않고 바로 답한다."
"""두 갈래와 심판에 똑같이 붙는다. 전역 AGENTS.md 가 파일을 읽으라고 해도 과제 하나에 도구를 쓰지 않게 한다."""
TASK = "주제: {topic}\n\n이 주제로 한국어 산문 한 편을 500자 안팎으로 쓴다. 제목 없이 본문만 낸다."
TIMEOUT = 900
"""호출 하나의 상한 (초). 이 기계의 Codex 는 추론 강도 xhigh 다."""


def prompt(arm: str, topic: str) -> str:
    """갈래의 프롬프트. craft 는 작법서 본문을 먼저 읽힌다."""
    body = f"{TOOL_RULE}\n\n{TASK.format(topic=topic)}"
    if arm == "craft":
        return f"{GUIDE.read_text(encoding='utf-8').strip()}\n\n---\n\n{body}"
    return body


def codex() -> str:
    found = shutil.which("codex")
    if not found:
        raise SystemExit("codex 를 PATH 에서 찾지 못했다")
    return found


def runCodex(text: str, outFile: Path) -> bool:
    """새 세션 하나에 프롬프트를 넣고 마지막 답을 outFile 에 쓴다. 비었거나 실패하면 False."""
    outFile.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="codexCraft-") as cwd:
        command = [codex(), "exec", "--skip-git-repo-check", "--ephemeral", "-s", "read-only", "-C", cwd]
        command += ["-o", str(outFile), "-"]
        try:
            done = subprocess.run(command, input=text.encode("utf-8"), capture_output=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            return False
    if done.returncode != 0 or not outFile.exists() or not outFile.read_text(encoding="utf-8").strip():
        outFile.unlink(missing_ok=True)
        return False
    return True


def meta(root: Path) -> None:
    """필자 조건. Codex 판과 설정 파일의 모델과 추론 강도."""
    version = subprocess.run([codex(), "--version"], capture_output=True, text=True, encoding="utf-8").stdout.strip()
    config = tomllib.loads((Path.home() / ".codex" / "config.toml").read_text(encoding="utf-8"))
    data = {"codex": version, "model": config.get("model"), "effort": config.get("model_reasoning_effort")}
    root.mkdir(parents=True, exist_ok=True)
    (root / "meta.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write(root: Path, workers: int, limit: int | None) -> str:
    """없는 글만 쓴다. 끊겨도 다시 돌리면 이어서 쓴다."""
    tasks = json.loads(TASKS.read_text(encoding="utf-8"))
    names = sorted(tasks)[:limit] if limit else sorted(tasks)
    meta(root)
    jobs = [(arm, name) for name in names for arm in ARMS if not (root / arm / f"{name}.md").exists()]

    def one(job: tuple[str, str]) -> tuple[str, str, bool]:
        arm, name = job
        ok = runCodex(prompt(arm, tasks[name]), root / arm / f"{name}.md")
        if not ok:
            ok = runCodex(prompt(arm, tasks[name]), root / arm / f"{name}.md")
        return arm, name, ok

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, jobs))
    failed = [f"{arm}/{name}" for arm, name, ok in results if not ok]
    lines = [f"새로 쓴 글 {len(results) - len(failed)}편, 실패 {len(failed)}편"]
    if failed:
        lines.append("실패: " + ", ".join(failed))
    return "\n".join(lines)


def answerArray(text: str) -> list:
    """마지막 답에서 JSON 배열 하나를 꺼낸다."""
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        raise ValueError("JSON 배열이 없다")
    value = json.loads(text[start : end + 1])
    if not isinstance(value, list):
        raise ValueError("배열이 아니다")
    return value


def gptJudge(batchDir: Path, outDir: Path, workers: int) -> str:
    """craftLift 의 심판 묶음을 Codex 에게 그대로 준다. 답은 묶음마다 JSON 파일 하나다."""
    outDir.mkdir(parents=True, exist_ok=True)
    batches = [p for p in sorted(batchDir.glob("judge-*.md")) if not (outDir / f"{p.stem}.json").exists()]

    def one(batch: Path) -> tuple[str, bool]:
        raw = outDir / f"{batch.stem}.txt"
        text = f"{TOOL_RULE}\n\n{batch.read_text(encoding='utf-8')}"
        for _ in range(2):
            if runCodex(text, raw):
                try:
                    items = answerArray(raw.read_text(encoding="utf-8"))
                except ValueError:
                    continue
                (outDir / f"{batch.stem}.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), "utf-8")
                return batch.stem, True
        return batch.stem, False

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, batches))
    failed = [name for name, ok in results if not ok]
    return f"묶음 {len(results) - len(failed)}개 판정, 실패 {len(failed)}개" + (f": {', '.join(failed)}" if failed else "")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("write")
    one.add_argument("root", type=Path)
    one.add_argument("--workers", type=int, default=4)
    one.add_argument("--limit", type=int, help="과제 이름 순서로 앞의 몇 개만. 시범 실행용")
    two = sub.add_parser("gptJudge")
    two.add_argument("batchDir", type=Path)
    two.add_argument("--output-dir", dest="outputDir", type=Path, required=True)
    two.add_argument("--workers", type=int, default=4)
    three = sub.add_parser("prompt", help="갈래 하나의 프롬프트를 그대로 찍는다")
    three.add_argument("arm", choices=ARMS)
    three.add_argument("taskId")
    args = parser.parse_args()
    if args.command == "write":
        print(write(args.root, args.workers, args.limit))
    elif args.command == "gptJudge":
        print(gptJudge(args.batchDir, args.outputDir, args.workers))
    else:
        tasks = json.loads(TASKS.read_text(encoding="utf-8"))
        print(prompt(args.arm, tasks[args.taskId]))


if __name__ == "__main__":
    main()
