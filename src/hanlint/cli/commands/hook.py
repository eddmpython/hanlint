"""`hanlint hook`. Claude Code의 저장과 답변 이벤트를 같은 규칙판으로 되먹임한다.

명령 훅의 JSON을 stdin에서 읽는다. PostToolUse에서는 Write와 Edit가 쓴 마크다운 하나를 저장소 설정으로
검사한다. `--reply`에서는 Stop의 마지막 답변을 chat 프리셋으로 검사한다. Finding이 없거나 입력을 읽을 수
없으면 침묵한다. 이 명령은 조언만 하므로 언제나 종료 코드 0이다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ...baseline import load
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from ...report import renderCompact
from ...rules import Finding, runAll
from .shared import MARKDOWN, configFrom

HELP = "저장하거나 답한 마크다운을 같은 턴에 검사한다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--reply", action="store_true", help="Stop의 마지막 답변을 chat 프리셋으로 검사한다")
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


def contextJson(eventName: str, name: str, findings: list[Finding]) -> str:
    """Claude Code가 다음 모델 요청에 넣는 비차단 Finding 문맥."""
    where = "마지막 답변" if eventName == "Stop" else "방금 쓴 마크다운"
    context = f"hanlint가 {where}에서 센 Finding입니다.\n{renderCompact(name, findings)}"
    value = {"hookSpecificOutput": {"hookEventName": eventName, "additionalContext": context}}
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def run(args: argparse.Namespace) -> int:
    try:
        payload = readPayload()
        if payload is None:
            return 0

        if args.reply:
            if payload.get("hook_event_name") != "Stop" or payload.get("stop_hook_active") is True:
                return 0
            text = payload.get("last_assistant_message")
            if not isinstance(text, str) or not text.strip():
                return 0
            cwd = payload.get("cwd")
            start = Path(cwd) if isinstance(cwd, str) and cwd else Path.cwd()
            config = configFrom(args, start=start)
            config.preset = "chat"
            eventName = "Stop"
            name = "<assistant>"
            findings = findingsFor(text, name, config, useBaseline=False)
        else:
            if payload.get("hook_event_name") != "PostToolUse" or payload.get("tool_name") not in ("Write", "Edit"):
                return 0
            toolInput = payload.get("tool_input")
            if not isinstance(toolInput, dict):
                return 0
            rawPath = toolInput.get("file_path")
            if not isinstance(rawPath, str) or not rawPath:
                return 0
            path = Path(rawPath)
            if path.suffix.lower() not in MARKDOWN or not path.is_file():
                return 0
            config = configFrom(args, start=path.parent)
            eventName = "PostToolUse"
            name = rawPath
            findings = findingsFor(path.read_text(encoding="utf-8"), name, config, useBaseline=True)

        if findings:
            sys.stdout.write(contextJson(eventName, name, findings) + "\n")
    except Exception:
        return 0
    return 0
