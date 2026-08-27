"""koreanStyleBooks. 한국 글쓰기 책들이 공통으로 지목하는 자리가 실제 글에 얼마나 있나.

이오덕 `우리글 바로쓰기`, 이수열 `우리말 우리글 바로 쓰기`, 김정선 `내 문장이 그렇게 이상한가요`,
배상복 `문장기술` 이 공통으로 드는 것들이다. 그 가운데 hanlint 가 아직 안 보는 것만 골랐다.

김정선이 유명하게 든 넷은 **적, 의, 것, 들** 이다. 그중 `의` 만 `euiChain` 이 본다. 나머지 셋이 비어 있다.
이오덕은 여기에 `가지다` 남용과 `~에 대하여` 를 더한다.

세는 것은 빈도뿐이다. 판정하지 않는다. 천 어절당 몇 번인지를 보고 규칙으로 만들 만한지는 사람이 정한다.
빈도가 높아도 정당한 용법이 대부분이면 규칙이 아니라 잡음이 된다. 그래서 표본 문장을 함께 낸다.

```powershell
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/koreanStyleBooks/probeStyleBooks.py <글들 폴더>
```
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from hanlint import fingerprint, loadConfig  # noqa: E402

SAMPLES = 3
"""자리마다 보일 표본 문장 수. 빈도만으로는 정당한 용법인지 알 수 없다."""

PATTERNS: dict[str, tuple[str, str]] = {
    "적(的)": (r"[가-힣]적(?:인|으로|이고|이며|이다|입니다)(?![가-힣])", "이오덕과 김정선. 한자어 뒤 적 은 대개 뺄 수 있다"),
    "것(의존명사)": (r"(?<![가-힣])것(?:은|이|을|으로|이다|입니다|이었|입니까)", "김정선. 것 은 대개 이름으로 바꿀 수 있다"),
    "들(복수)": (r"[가-힣]들(?:은|이|을|의|과|에게|에|도|만)(?![가-힣])", "이오덕. 한국어는 복수 표지를 잘 안 쓴다"),
    "가지다": (r"(?:가지|갖)(?:고 있|는다|습니다|다|었)", "이오덕. have 번역투다. 있다 로 쓴다"),
    "에 대하여": (r"에 (?:대하여|대해서|대한|대해)", "이오덕. 영어 about 의 번역투다"),
    "시키다": (r"[가-힣]시(?:키|켰|킵니다|킨다)", "이수열. 사동이 아닌 자리에 시키다 를 붙이는 것"),
    "~중이다": (r"[가-힣] 중(?:이|입니다|이다|인)", "배상복. 진행형 번역투다"),
    "보여지다": (r"(?:보여지|여겨지|생각되)", "이오덕. 이중 피동의 다른 꼴"),
}


def report(folder: Path) -> str:
    config = loadConfig(start=folder)
    sentences = []
    for path in sorted(folder.rglob("*.md"), key=str):
        doc = fingerprint(path.read_text(encoding="utf-8"), config, path=str(path))
        sentences.extend((path.name, s.text) for s in doc.sentences)
    words = sum(len(text.split()) for _, text in sentences)
    lines = [f"대상   {folder}", f"문장 {len(sentences)}개, 어절 {words}개", ""]
    for label, (pattern, source) in PATTERNS.items():
        compiled = re.compile(pattern)
        hits = [(name, text) for name, text in sentences if compiled.search(text)]
        rate = len(hits) * 1000 / words if words else 0.0
        lines.append(f"{label:12} {len(hits):3}건  천 어절당 {rate:5.2f}  {source}")
        for name, text in hits[:SAMPLES]:
            found = compiled.search(text)
            lines.append(f"    {name[:18]:20} …{text[max(0, found.start() - 18) : found.end() + 18]}…")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if not argv:
        print("글들이 든 폴더 하나를 인자로 준다", file=sys.stderr)
        return 2
    print(report(Path(argv[0])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
