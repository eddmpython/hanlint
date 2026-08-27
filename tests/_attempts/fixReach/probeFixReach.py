"""fixReach. 지적 가운데 기계가 고쳐 주는 것이 몇 건인가.

hanlint 는 자리와 이유를 준다. 그다음 고치는 일은 누가 하는가. `hanlint fix` 가 닿는 자리는 확정 치환이
있는 지적뿐이고 나머지는 전부 글쓴이 (또는 AI) 의 몫이다. 그 비율을 모르면 도구가 실제로 글을 고치게
만들었는지 말할 수 없다.

재는 축 셋이다.

- **fixRate**: 전체 지적 가운데 `replacement` 를 든 것의 비율. `hanlint fix` 가 원문에 넣는 자리다
- **guideRate**: `fix` 문자열 (고친 뒤 문장) 을 든 것의 비율. 치환은 못 해도 본보기는 있는 자리다
- **bareRate**: 둘 다 없는 것의 비율. 지적만 받고 어떻게 고칠지는 이유 문장에서 읽어 내야 하는 자리

규칙별로도 나눠 적는다. 어느 규칙이 사람을 가장 많이 헤매게 하는지가 거기서 나온다.

판정하지 않는다. 분포만 낸다.

```powershell
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/fixReach/probeFixReach.py <글들 폴더>
```
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from hanlint import Finding, lintFile, loadConfig  # noqa: E402


def findingsIn(folder: Path) -> dict[str, list[Finding]]:
    config = loadConfig(start=folder)
    found: dict[str, list[Finding]] = {}
    for path in sorted(folder.rglob("*.md"), key=str):
        found[path.name] = lintFile(path, config)
    return found


def kindOf(finding: Finding) -> str:
    if finding.replacement is not None:
        return "fix"
    if finding.fix:
        return "guide"
    return "bare"


def report(folder: Path) -> str:
    results = findingsIn(folder)
    findings = [f for found in results.values() for f in found]
    if not findings:
        return f"{folder} 에서 지적이 0 이다. 잴 것이 없다"
    kinds = Counter(kindOf(f) for f in findings)
    total = len(findings)
    lines = [
        f"대상   {folder}",
        f"글     {len(results)}편, 지적 {total}건 (error {sum(1 for f in findings if f.severity == 'error')})",
        "",
        f"fix    {kinds['fix']:3}건 ({kinds['fix'] / total:5.1%})  기계가 원문에 넣는다",
        f"guide  {kinds['guide']:3}건 ({kinds['guide'] / total:5.1%})  고친 문장은 있고 치환은 못 한다",
        f"bare   {kinds['bare']:3}건 ({kinds['bare'] / total:5.1%})  이유만 있고 본보기가 없다",
        "",
        "규칙별 (bare 가 많은 순)",
    ]
    byRule: dict[str, Counter] = {}
    for finding in findings:
        byRule.setdefault(finding.rule, Counter())[kindOf(finding)] += 1
    order = sorted(byRule.items(), key=lambda item: (-item[1]["bare"], item[0]))
    for name, counts in order:
        total = sum(counts.values())
        lines.append(f"  {name:22} 합 {total:3}  fix {counts['fix']:3}  guide {counts['guide']:3}  bare {counts['bare']:3}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if not argv:
        print("글들이 든 폴더 하나를 인자로 준다", file=sys.stderr)
        return 2
    print(report(Path(argv[0])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
