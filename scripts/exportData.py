"""파이썬 data/ 와 규칙 docstring 을 npm 패키지의 data/ 로 투영한다.

정본은 src/hanlint/data 와 규칙 파일의 docstring 이다. txt 는 그대로, toml 은 json 으로, docstring 은
ruleDocs.json 으로 간다. 만든 것을 손으로 고치지 않는다. tests/gates/testNpmData.py 가 투영이 정본과
같은지 본다. `python scripts/exportData.py --check` 가 같은 검사다.
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "hanlint" / "data"
TARGET = ROOT / "npm" / "data"
LICENSE_SOURCE = ROOT / "LICENSE"
LICENSE_TARGET = ROOT / "npm" / "LICENSE"
"""MIT 전문의 정본은 뿌리 LICENSE 하나다. npm 은 패키지 뿌리에서만 라이선스를 찾으므로 그리로 투영한다.
휠은 pyproject 의 license-files 로 같은 정본을 담는다. 0.0.7 까지 npm 판만 전문 없이 나갔다."""
PYTHON_ONLY_DATA = {
    "blueprints.json",
    "evidenceEntailmentV1.json",
    "learningVocabularySource.toml",
    "writingArenaPilotV1.json",
}
"""npm 명령이 쓰지 않는 파이썬 전용 자료. TSV 는 투영 대상 확장자에 처음부터 들지 않는다."""


def render() -> dict[str, str]:
    """파일 이름 → 내용. 결정적이라 같은 정본이면 같은 결과다."""
    files: dict[str, str] = {}
    for path in sorted(SOURCE.iterdir()):
        if path.name in PYTHON_ONLY_DATA:
            continue
        if path.suffix in (".txt", ".json"):
            files[path.name] = path.read_text(encoding="utf-8")
        elif path.suffix == ".toml":
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            files[path.stem + ".json"] = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    sys.path.insert(0, str(ROOT / "src"))
    from hanlint import __version__
    from hanlint.rules import ruleCategories, ruleDoc, ruleMechanisms, ruleNames

    docs = {name: ruleDoc(name) for name in ruleNames()}
    files["ruleDocs.json"] = json.dumps(docs, ensure_ascii=False, indent=2) + "\n"
    # 부류의 정본은 규칙 파일이 사는 폴더다. npm 은 폴더를 걸어 찾지 않으므로 투영으로 받는다.
    files["ruleCategories.json"] = json.dumps(ruleCategories(), ensure_ascii=False, indent=2) + "\n"
    # 기제의 정본은 규칙 파일의 등록 인자다. npm 은 같은 대응을 투영으로 받고 시험이 두 판을 견준다.
    files["ruleMechanisms.json"] = json.dumps(ruleMechanisms(), ensure_ascii=False, indent=2) + "\n"
    files["version.json"] = json.dumps({"version": __version__}) + "\n"
    return files


def staleFiles(files: dict[str, str]) -> list[str]:
    """정본과 다른 투영 파일 이름. 없어야 정상이다."""
    stale = []
    for name, content in files.items():
        target = TARGET / name
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            stale.append(name)
    if TARGET.exists():
        stale.extend(f"{p.name} (정본에 없다)" for p in sorted(TARGET.iterdir()) if p.name not in files)
    return stale


def main(argv: list[str]) -> int:
    files = render()
    licenseText = LICENSE_SOURCE.read_text(encoding="utf-8")
    if "--check" in argv:
        stale = staleFiles(files)
        if not LICENSE_TARGET.exists() or LICENSE_TARGET.read_text(encoding="utf-8") != licenseText:
            stale.append("../LICENSE (뿌리 LICENSE 와 다르다)")
        if stale:
            print("npm/data 가 정본과 다르다. python scripts/exportData.py 를 돌린다: " + ", ".join(stale))
            return 1
        print("npm/data 가 정본과 같다")
        return 0
    TARGET.mkdir(parents=True, exist_ok=True)
    for path in TARGET.iterdir():
        if path.is_file() and path.name not in files:
            path.unlink()
    for name, content in files.items():
        (TARGET / name).write_text(content, encoding="utf-8", newline="\n")
    LICENSE_TARGET.write_text(licenseText, encoding="utf-8", newline="\n")
    print(f"{len(files)}개와 LICENSE 를 {TARGET.parent} 에 썼다")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
