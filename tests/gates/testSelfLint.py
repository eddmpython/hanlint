"""이 저장소의 글을 hanlint 자신이 검사한다. 자기 규칙을 못 지키는 린터는 신뢰를 잃는다.

README 와 skills/specs 의 모든 마크다운이 error 급 지적 없이 통과해야 한다. 설정은 저장소 루트의
hanlint.toml 이다. 음성 시험은 같은 검사기에 상투어를 넣은 문서를 만들어 잡히는지 본다.
"""

from __future__ import annotations

from pathlib import Path

from hanlint import lintText, loadConfig

ROOT = Path(__file__).resolve().parents[2]
CONFIG = loadConfig(ROOT / "hanlint.toml")


def documents() -> list[Path]:
    return [
        ROOT / "README.md",
        ROOT / "npm" / "README.md",
        ROOT / "vscode" / "README.md",
        *sorted((ROOT / "skills").rglob("*.md")),
        *sorted((ROOT / "tests" / "_attempts").rglob("*.md")),
        *sorted((ROOT / "tests" / "fixtures").glob("*.md")),
    ]


def errorsIn(path: Path) -> list[str]:
    findings = lintText(path.read_text(encoding="utf-8"), CONFIG, path=str(path))
    return [f"{path.relative_to(ROOT).as_posix()}:{f.line} [{f.rule}] {f.quote[:60]}" for f in findings if f.severity == "error"]


def testOwnDocumentsPassOwnRules():
    problems = [problem for path in documents() for problem in errorsIn(path)]
    assert problems == []


def testGateBites():
    findings = lintText("## 절\n\n핵심은 속도입니다. 이것으로 됩니다.\n", CONFIG)
    assert {f.rule for f in findings} >= {"cliche"}
