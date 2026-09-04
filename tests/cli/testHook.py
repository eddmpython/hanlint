"""Claude Code 훅 입력을 비차단 Finding 문맥으로 바꾸는 계약."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from hanlint.cli.main import main


def runHook(monkeypatch, capsys, args: list[str], payload: object | str) -> tuple[int, str, str]:
    raw = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(raw))
    code = main(["hook", *args])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def postPayload(path: Path, toolName: str = "Write") -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": toolName,
        "tool_input": {"file_path": str(path)},
        "tool_response": {"success": True},
    }


def testWrittenMarkdownBecomesAdditionalContext(tmp_path, monkeypatch, capsys):
    draft = tmp_path / "초안.md"
    draft.write_text("## 절\n\n핵심은 속도입니다.\n", encoding="utf-8")

    code, out, err = runHook(monkeypatch, capsys, [], postPayload(draft, "Edit"))

    assert code == 0 and err == ""
    result = json.loads(out)
    hookOutput = result["hookSpecificOutput"]
    assert hookOutput["hookEventName"] == "PostToolUse"
    assert "방금 쓴 마크다운에서 센 Finding" in hookOutput["additionalContext"]
    assert f"{draft}:3 [cliche]" in hookOutput["additionalContext"]


def testReplyUsesChatPresetOnce(monkeypatch, capsys, tmp_path):
    payload = {
        "hook_event_name": "Stop",
        "cwd": str(tmp_path),
        "stop_hook_active": False,
        "last_assistant_message": "결과가 저장되어집니다.",
    }
    code, out, err = runHook(monkeypatch, capsys, ["--reply"], payload)

    assert code == 0 and err == ""
    result = json.loads(out)
    hookOutput = result["hookSpecificOutput"]
    assert hookOutput["hookEventName"] == "Stop"
    assert "<assistant>:1 [doublePassive]" in hookOutput["additionalContext"]

    payload["stop_hook_active"] = True
    assert runHook(monkeypatch, capsys, ["--reply"], payload) == (0, "", "")


def testHookStaysSilentForCleanOrUnusableInput(tmp_path, monkeypatch, capsys):
    clean = tmp_path / "clean.md"
    clean.write_text("## 절\n\n파일을 엽니다. 그러면 표가 생길까요? 작업 폴더에 생깁니다.\n", encoding="utf-8")
    plain = tmp_path / "note.txt"
    plain.write_text("핵심은 속도입니다.\n", encoding="utf-8")
    missing = tmp_path / "missing.md"

    cases: list[tuple[list[str], object | str]] = [
        ([], postPayload(clean)),
        ([], postPayload(plain)),
        ([], postPayload(missing)),
        ([], postPayload(clean, "Read")),
        ([], {"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {}}),
        (["--reply"], {"hook_event_name": "Stop", "stop_hook_active": False, "last_assistant_message": ""}),
        ([], "not json"),
    ]
    for args, payload in cases:
        assert runHook(monkeypatch, capsys, args, payload) == (0, "", "")
