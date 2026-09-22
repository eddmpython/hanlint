"""`hanlint hook`. 에이전트 훅에서 쓰기 전에는 작법서를 싣고, 쓴 뒤에는 같은 규칙판으로 되먹임한다.

명령 훅의 JSON을 stdin에서 읽는다. `--prime`에서는 SessionStart와 UserPromptSubmit 입력에 작법서
(data/koreanProse.txt) 본문을 additionalContext로 낸다. Claude Code와 Codex가 같은 JSON 꼴을 받는다.
PostToolUse에서는 쓴 마크다운을 저장소 설정으로 검사한다. Claude Code는 Write와 Edit의 `file_path`를, Codex는
`apply_patch`의 패치 본문 (`tool_input.command`) 머리 줄을 준다. `--reply`에서는 Stop의 마지막 답변을 chat
프리셋으로 검사한다. Claude Code에는 additionalContext로, `--agent codex`면 Codex가 Stop에서 받는 `systemMessage`로
낸다. 둘 다 막지 않는다. 낼 것이 없거나 입력을 읽을 수 없으면 침묵한다. 이 명령은 조언만 하므로 언제나 종료
코드 0이다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ...baseline import load
from ...data import proseGuide
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from ...report import renderCompact
from ...rules import Finding, runAll
from .shared import MARKDOWN, configFrom

HELP = "쓰기 전에 작법서를 싣고, 저장하거나 답한 마크다운을 같은 턴에 검사한다"
PRIME_EVENTS = ("SessionStart", "UserPromptSubmit")
"""작법서를 싣는 이벤트. Claude Code와 Codex 모두 이 둘의 additionalContext를 모델 문맥에 넣는다."""
AGENTS = ("claude", "codex")
PATCH_HEADS = ("*** Add File: ", "*** Update File: ", "*** Move to: ")
"""Codex apply_patch 본문에서 쓴 파일을 가리키는 머리 줄 (Codex 훅 문서, 2026-09-21 확인)."""


def addParser(parser: argparse.ArgumentParser) -> None:
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prime", action="store_true", help="SessionStart나 UserPromptSubmit에 작법서 본문을 싣는다")
    mode.add_argument("--reply", action="store_true", help="Stop의 마지막 답변을 chat 프리셋으로 검사한다")
    parser.add_argument("--agent", choices=AGENTS, default="claude", help="Stop 출력 꼴. codex는 systemMessage로 낸다")
    parser.add_argument("--config", type=Path, help="설정 파일. 없으면 쓴 파일이나 현재 폴더에서 찾는다")
    parser.add_argument("--preset", help="저장한 파일에 적용할 글 종류. --reply에서는 chat으로 고정한다")
    parser.add_argument("--disable", action="append", default=[], metavar="RULE", help="이번 실행에서 끌 규칙")


def readPayload() -> dict | None:
    """stdin의 UTF-8 JSON 객체. 훅 입력이 아니면 None이다."""
    stream = getattr(sys.stdin, "buffer", sys.stdin)
    raw = stream.read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    value = json.loads(raw)
    return value if isinstance(value, dict) else None


def findingsFor(text: str, name: str, config, useBaseline: bool) -> list[Finding]:
    """본문 하나의 Finding. 저장 훅은 일반 lint와 같은 잠금을 적용한다."""
    document = buildFingerprint(parseMarkdown(text, path=name), config)
    findings = runAll(document, config)
    if not useBaseline or not config.baseline:
        return findings
    baseline = load(Path(config.baseline))
    return baseline.keep(name, findings)


def contextJson(eventName: str, context: str) -> str:
    """에이전트가 다음 모델 요청에 넣는 비차단 문맥."""
    value = {"hookSpecificOutput": {"hookEventName": eventName, "additionalContext": context}}
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def findingContext(eventName: str, found: list[tuple[str, list[Finding]]]) -> str:
    """Finding을 되먹이는 문맥의 본문. 파일마다 한 덩어리다."""
    where = "마지막 답변" if eventName == "Stop" else "방금 쓴 마크다운"
    return f"hanlint가 {where}에서 센 Finding입니다.\n" + "\n".join(renderCompact(name, items) for name, items in found)


def patchPaths(patch: str) -> list[str]:
    """apply_patch 본문이 쓴 파일 경로. 나온 차례대로 한 번씩이다."""
    paths: list[str] = []
    for line in patch.splitlines():
        for head in PATCH_HEADS:
            if line.startswith(head) and (path := line[len(head) :].strip()) and path not in paths:
                paths.append(path)
    return paths


def writtenPaths(payload: dict) -> list[str]:
    """PostToolUse 입력이 쓴 파일 경로. 모르는 도구면 빈 목록이다."""
    toolInput = payload.get("tool_input")
    if not isinstance(toolInput, dict):
        return []
    if payload.get("tool_name") in ("Write", "Edit"):
        path = toolInput.get("file_path")
        return [path] if isinstance(path, str) and path else []
    if payload.get("tool_name") == "apply_patch":
        patch = toolInput.get("command")
        return patchPaths(patch) if isinstance(patch, str) else []
    return []


def written(payload: dict, args: argparse.Namespace) -> list[tuple[str, list[Finding]]]:
    """쓴 마크다운마다 (이름, Finding). 상대 경로는 입력의 cwd에서 찾는다."""
    cwd = payload.get("cwd")
    base = Path(cwd) if isinstance(cwd, str) and cwd else None
    found = []
    for rawPath in writtenPaths(payload):
        path = Path(rawPath)
        if base is not None and not path.is_absolute():
            path = base / path
        if path.suffix.lower() not in MARKDOWN or not path.is_file():
            continue
        config = configFrom(args, start=path.parent)
        found.append((rawPath, findingsFor(path.read_text(encoding="utf-8"), rawPath, config, useBaseline=True)))
    return found


def run(args: argparse.Namespace) -> int:
    try:
        payload = readPayload()
        if payload is None:
            return 0

        eventName = payload.get("hook_event_name")
        if args.prime:
            if eventName in PRIME_EVENTS:
                sys.stdout.write(contextJson(eventName, proseGuide()) + "\n")
            return 0

        if args.reply:
            if eventName != "Stop" or payload.get("stop_hook_active") is True:
                return 0
            text = payload.get("last_assistant_message")
            if not isinstance(text, str) or not text.strip():
                return 0
            cwd = payload.get("cwd")
            start = Path(cwd) if isinstance(cwd, str) and cwd else Path.cwd()
            config = configFrom(args, start=start)
            config.preset = "chat"
            found = [("<assistant>", findingsFor(text, "<assistant>", config, useBaseline=False))]
        elif eventName == "PostToolUse":
            found = written(payload, args)
        else:
            return 0

        found = [(name, items) for name, items in found if items]
        if not found:
            return 0
        context = findingContext(eventName, found)
        if args.reply and args.agent == "codex":
            sys.stdout.write(json.dumps({"systemMessage": context}, ensure_ascii=False, separators=(",", ":")) + "\n")
        else:
            sys.stdout.write(contextJson(eventName, context) + "\n")
    except Exception:
        return 0
    return 0
