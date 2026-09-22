"""에이전트 훅 입력을 쓰기 전 작법서와 비차단 Finding 문맥으로 바꾸는 계약."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from hanlint.cli.main import main
from hanlint.data import proseGuide


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


def testPrimeCarriesTheGuideBeforeWriting(monkeypatch, capsys):
    """Claude Code와 Codex가 같은 꼴을 받는다. 이벤트 이름을 그대로 돌려주고 본문은 작법서 파일 그대로다."""
    for eventName in ("SessionStart", "UserPromptSubmit"):
        code, out, err = runHook(monkeypatch, capsys, ["--prime"], {"hook_event_name": eventName, "cwd": "."})
        assert code == 0 and err == ""
        hookOutput = json.loads(out)["hookSpecificOutput"]
        assert hookOutput == {"hookEventName": eventName, "additionalContext": proseGuide()}


def testPrimeStaysSilentOutsideItsEvents(tmp_path, monkeypatch, capsys):
    draft = tmp_path / "초안.md"
    draft.write_text("## 절\n\n핵심은 속도입니다.\n", encoding="utf-8")
    cases: list[object | str] = [
        {"hook_event_name": "Stop", "last_assistant_message": "결과가 저장되어집니다."},
        postPayload(draft),
        {},
        "not json",
    ]
    for payload in cases:
        assert runHook(monkeypatch, capsys, ["--prime"], payload) == (0, "", "")


def testPrimeAndReplyAreExclusive(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    try:
        main(["hook", "--prime", "--reply"])
    except SystemExit as stop:
        assert stop.code == 2
    else:
        raise AssertionError("--prime 과 --reply 를 함께 받았다")
    assert "not allowed with" in capsys.readouterr().err


def patchPayload(cwd: Path, patch: str, toolName: str = "apply_patch") -> dict:
    """Codex 훅 문서의 PostToolUse 꼴. 패치 본문은 tool_input.command 에 온다."""
    return {"hook_event_name": "PostToolUse", "cwd": str(cwd), "tool_name": toolName, "tool_input": {"command": patch}}


def testCodexPatchChecksEveryWrittenMarkdown(tmp_path, monkeypatch, capsys):
    (tmp_path / "초안.md").write_text("## 절\n\n핵심은 속도입니다.\n", encoding="utf-8")
    (tmp_path / "clean.md").write_text("## 절\n\n파일을 엽니다. 그러면 표가 생길까요? 작업 폴더에 생깁니다.\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "new.md").write_text("## 절\n\n결과가 저장되어집니다.\n", encoding="utf-8")
    (tmp_path / "note.txt").write_text("핵심은 속도입니다.\n", encoding="utf-8")
    patch = "\n".join(
        [
            "*** Begin Patch",
            "*** Add File: 초안.md",
            "+핵심은 속도입니다.",
            "*** Update File: clean.md",
            "@@",
            "*** Update File: docs/old.md",
            "*** Move to: docs/new.md",
            "*** Update File: note.txt",
            "*** End Patch",
        ]
    )
    code, out, err = runHook(monkeypatch, capsys, [], patchPayload(tmp_path, patch))

    assert code == 0 and err == ""
    context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("hanlint가 방금 쓴 마크다운에서 센 Finding입니다.\n")
    assert "초안.md:3 [cliche]" in context
    assert "docs/new.md:3 [doublePassive]" in context
    assert "clean.md" not in context and "note.txt" not in context and "old.md" not in context


def testCodexPatchStaysSilentOutsideWrites(tmp_path, monkeypatch, capsys):
    (tmp_path / "clean.md").write_text("## 절\n\n파일을 엽니다. 그러면 표가 생길까요? 작업 폴더에 생깁니다.\n", encoding="utf-8")
    cases: list[object] = [
        patchPayload(tmp_path, "*** Begin Patch\n*** Update File: clean.md\n*** End Patch"),
        patchPayload(tmp_path, "*** Begin Patch\n*** Delete File: 초안.md\n*** End Patch"),
        patchPayload(tmp_path, "*** Add File: 초안.md", toolName="exec_command"),
        {"hook_event_name": "PostToolUse", "cwd": str(tmp_path), "tool_name": "apply_patch", "tool_input": {}},
    ]
    for payload in cases:
        assert runHook(monkeypatch, capsys, [], payload) == (0, "", "")


def testCodexReplyUsesSystemMessage(monkeypatch, capsys, tmp_path):
    """Codex 의 Stop 은 additionalContext 를 받지 않는다. 막지 않는 systemMessage 로 사용자에게 보인다."""
    payload = {
        "hook_event_name": "Stop",
        "cwd": str(tmp_path),
        "turn_id": "t",
        "stop_hook_active": False,
        "last_assistant_message": "결과가 저장되어집니다.",
    }
    code, out, err = runHook(monkeypatch, capsys, ["--reply", "--agent", "codex"], payload)

    assert code == 0 and err == ""
    result = json.loads(out)
    assert list(result) == ["systemMessage"]
    assert "<assistant>:1 [doublePassive]" in result["systemMessage"]
    payload["stop_hook_active"] = True
    assert runHook(monkeypatch, capsys, ["--reply", "--agent", "codex"], payload) == (0, "", "")


def testUnknownAgentIsUsageError(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    try:
        main(["hook", "--reply", "--agent", "grok"])
    except SystemExit as stop:
        assert stop.code == 2
    else:
        raise AssertionError("모르는 --agent 를 받았다")
    assert "invalid choice" in capsys.readouterr().err


def testHookLabelsStyleNotices(tmp_path, monkeypatch, capsys):
    draft = tmp_path / "draft.md"
    draft.write_text("가상환경 생성 후 패키지 설치 확인 절차를 따릅니다.", encoding="utf-8")
    code, out, err = runHook(monkeypatch, capsys, [], postPayload(draft))
    assert code == 0 and not err
    assert "[nounPile] notice:" in json.loads(out)["hookSpecificOutput"]["additionalContext"]


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
