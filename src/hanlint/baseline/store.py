"""이미 있는 지적을 baseline 파일에 적어 두고 새로 생긴 지적만 막는다. 팀이 도구를 끄지 않게 하는 부분이다.

**왜 이 부분이 있는가.** 남의 저장소 문서 여섯 편에 그냥 돌려 보니 오류가 25건 나왔다(2026-08-27). 규칙이
틀려서가 아니라 그 글들이 실제로 문단이 조각나 있고 제목이 문장이기 때문이다. 그런데 첫날 25건을 보는 팀은
도구를 끈다. 그러면 hanlint는 한 사람만 쓰는 도구로 남는다.

**왜 줄 번호가 아니라 글자인가.** 코드 린터의 baseline은 파일과 줄 번호로 지적을 적는다. 글은 그렇게 할 수
없다. 문단 하나만 고쳐도 아래 줄 번호가 모두 밀려 baseline 파일에 든 지적이 모두 풀린다. hanlint는 글 분석 결과에
지적의 인용문을 그대로 들고 있으므로 **인용문의 글자로 적는다.**

그래서 성질 하나가 저절로 따라온다. **손댄 문장만 막는다.**

- 문장이 위치만 옮기면 인용문이 같으므로 여전히 baseline 파일에 든 지적이다. 잘못된 경고가 나지 않는다
- 문장을 고치면 인용문이 달라져 새 지적이 된다. 손댔으면 책임진다는 뜻이고 그게 맞다
- 문장을 지우면 baseline 파일에 그 지적이 남는다. `--prune`이 지운다

기한이나 비율을 정하지 않아도 글을 고칠 때마다 baseline 파일의 지적이 저절로 줄어든다. 이 설계를 고른 까닭이다.

파일은 사람이 읽는 형식이다. 해시로 줄이면 작아지지만 PR을 보는 사람이 어떤 지적이 들었는지 못 본다. 든 지적을
리뷰할 수 있어야 baseline이 고칠 일을 감추는 파일이 되지 않는다.

경로는 **baseline 파일이 있는 폴더에서 본 상대 경로**로 적는다. 팀이 커밋해 함께 쓰는 파일이라 입력한 그대로
(윈도의 절대 경로) 적으면 CI에서 아무 지적도 걸러지지 않는다. 적을 때와 찾을 때 같은 함수를 거친다.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from ..rules import Finding

DEFAULT_NAME = ".hanlint-baseline.json"
"""기본 파일 이름. 저장소에 커밋해서 팀이 함께 본다."""
VERSION = 1


def normalizeQuote(quote: str) -> str:
    """줄바꿈과 이어진 공백을 하나로 눕힌다. 문단을 다시 흘려도 같은 문장은 같은 글자다."""
    return " ".join(quote.split())


def keyOf(finding: Finding) -> tuple[str, str]:
    return finding.rule, normalizeQuote(finding.quote)


def pathKey(path: str, target: str | Path | None) -> str:
    """baseline 파일이 있는 폴더에서 본 상대 경로. 어느 기계에서 어떻게 입력했든 같은 글에 같은 키가 나온다."""
    if target is None or not path or path.startswith("<"):
        return path
    base = Path(target).resolve().parent
    try:
        return Path(os.path.relpath(Path(path).resolve(), base)).as_posix()
    except ValueError:  # 윈도에서 드라이브가 다르면 상대 경로가 없다
        return Path(path).resolve().as_posix()


@dataclass(frozen=True)
class Baseline:
    """파일 키 → baseline 파일에 든 (규칙, 인용문) 집합. 키는 `source`가 있는 폴더에서 본 경로다."""

    locked: dict[str, set[tuple[str, str]]] = field(default_factory=dict)
    source: str | None = None

    @property
    def count(self) -> int:
        return sum(len(entries) for entries in self.locked.values())

    def isLocked(self, path: str, finding: Finding) -> bool:
        return keyOf(finding) in self.locked.get(pathKey(path, self.source), set())

    def keep(self, path: str, findings: list[Finding]) -> list[Finding]:
        """baseline 파일에 없는 지적만 남긴다."""
        return [f for f in findings if not self.isLocked(path, f)]


def build(results: dict[str, list[Finding]], target: str | Path | None = None) -> Baseline:
    locked = {pathKey(p, target): {keyOf(f) for f in findings} for p, findings in results.items() if findings}
    return Baseline(locked, str(Path(target).resolve()) if target else None)


def render(baseline: Baseline) -> str:
    """사람이 읽고 리뷰하는 형식. 파일 이름과 (규칙, 인용문)을 정렬해 담아 같은 입력에 같은 파일이 나온다."""
    files = {
        path: [{"rule": rule, "quote": quote} for rule, quote in sorted(entries)]
        for path, entries in sorted(baseline.locked.items())
        if entries
    }
    data = {"version": VERSION, "locked": sum(len(v) for v in files.values()), "files": files}
    return json.dumps(data, ensure_ascii=False, indent=2)


def parse(text: str, source: str | None = None) -> Baseline:
    data = json.loads(text)
    if data.get("version") != VERSION:
        raise ValueError(f"지원하지 않는 baseline 버전: {data.get('version')}. hanlint baseline으로 다시 만든다")
    locked = {path: {(e["rule"], e["quote"]) for e in entries} for path, entries in data.get("files", {}).items()}
    return Baseline(locked, source)


def load(path: str | Path) -> Baseline:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(2, "찾지 못했다", str(target))
    return parse(target.read_text(encoding="utf-8"), str(target.resolve()))


def prune(baseline: Baseline, results: dict[str, list[Finding]]) -> Baseline:
    """지금 글에 더는 없는 지적을 baseline 파일에서 지운다. 검사한 파일만 손대므로 안 본 파일의 지적은 남는다."""
    kept = dict(baseline.locked)
    for path, findings in results.items():
        key = pathKey(path, baseline.source)
        present = {keyOf(f) for f in findings}
        remaining = kept.get(key, set()) & present
        if remaining:
            kept[key] = remaining
        else:
            kept.pop(key, None)
    return Baseline(kept, baseline.source)
