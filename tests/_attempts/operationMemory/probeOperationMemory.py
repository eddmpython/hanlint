"""공개 Git 교정 이력에서 사실 보존형 편집 연산 후보를 채굴한다.

저장소 사본과 원시 산출물은 프로젝트 밖 공통 실행 공간에 둔다. 이 스크립트에는 공개 저장소 주소,
라이선스 경로, 채굴 규칙만 남긴다. 커밋 제목이 교정을 말해도 숫자나 코드 같은 보호 원자가 바뀌거나
문장 대응이 모호하면 승격 후보로 보지 않는다.

```powershell
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/operationMemory/probeOperationMemory.py harvest `
  C:/Users/MSI/AppData/Local/dev-workspace/hanlint-operation-memory-20260831 `
  --output C:/Users/MSI/AppData/Local/dev-workspace/hanlint-operation-memory-20260831/harvest.json
```
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXEMPLAR_PROBE = ROOT / "tests" / "_attempts" / "exemplarLift"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(EXEMPLAR_PROBE))

from probeExemplarLift import (  # noqa: E402
    OLLAMA_ENDPOINT,
    OLLAMA_OPTIONS,
    ollamaGenerate,
    ollamaInfo,
    readJson,
)

from hanlint import Config, learnText  # noqa: E402
from hanlint.analysis import splitSentences  # noqa: E402
from hanlint.data.operations import SurfaceOperation as ProductSurfaceOperation  # noqa: E402
from hanlint.data.operations import (  # noqa: E402
    applyOperation,
    changedFragment,
    operationFromApproval,
    protectedAtoms,
)
from hanlint.document import plainText  # noqa: E402

KOREAN = re.compile(r"[가-힣]")
CORRECTION = re.compile(
    r"오타|교정|문장|표현|맞춤법|띄어쓰기|다듬|명확|자연|polish|typo|grammar|wording|proofread|clarity",
    re.IGNORECASE,
)
CONTENT_CHANGE = re.compile(
    r"번역|translate|sync|update|추가|삭제|누락|mistranslation|기능|링크|link|release|version",
    re.IGNORECASE,
)
MARKDOWN_PREFIX = re.compile(r"^(?:\s*(?:[-*+] |\d+[.)] |>+ |#{1,6} ))+")
SPACE = re.compile(r"\s+")
EXPERIMENT_CONDITIONS = ("reasonOnly", "blindExemplar", "exactReplay", "operationPatch")


@dataclass(frozen=True)
class Repository:
    id: str
    repo: str
    license: str
    licensePath: str
    domain: str
    pathspecs: tuple[str, ...]


REPOSITORIES = (
    Repository(
        id="mdnKo",
        repo="https://github.com/mdn/translated-content",
        license="CC-BY-SA-2.5",
        licensePath="LICENSE.md",
        domain="MDN 한국어 웹 기술 참고 문서",
        pathspecs=("files/ko/*.md", "files/ko/**/*.md"),
    ),
    Repository(
        id="kubernetesKo",
        repo="https://github.com/kubernetes/website",
        license="CC-BY-4.0",
        licensePath="LICENSE",
        domain="쿠버네티스 한국어 운영 문서와 블로그",
        pathspecs=(
            "content/ko/docs/*.md",
            "content/ko/docs/**/*.md",
            "content/ko/blog/*.md",
            "content/ko/blog/**/*.md",
        ),
    ),
    Repository(
        id="reactKo",
        repo="https://github.com/reactjs/ko.react.dev",
        license="CC-BY-4.0",
        licensePath="LICENSE-DOCS.md",
        domain="React 한국어 참고 문서와 학습서",
        pathspecs=("src/content/**/*.md",),
    ),
    Repository(
        id="vueKo",
        repo="https://github.com/vuejs-translations/docs-ko",
        license="CC-BY-4.0",
        licensePath="LICENSE",
        domain="Vue 한국어 참고 문서와 튜토리얼",
        pathspecs=("src/**/*.md",),
    ),
    Repository(
        id="rustKo",
        repo="https://github.com/rust-kr/doc.rust-kr.org",
        license="MIT OR Apache-2.0",
        licensePath="LICENSE-MIT AND LICENSE-APACHE",
        domain="러스트 한국어 프로그래밍 교재",
        pathspecs=(
            "src/*.md",
            "src/**/*.md",
            "second-edition/src/*.md",
            "second-edition/src/**/*.md",
            "2018-edition/src/*.md",
            "2018-edition/src/**/*.md",
        ),
    ),
    Repository(
        id="fastapi",
        repo="https://github.com/fastapi/fastapi",
        license="MIT",
        licensePath="LICENSE",
        domain="FastAPI 한국어 참고 문서",
        pathspecs=("docs/ko/docs/*.md", "docs/ko/docs/**/*.md"),
    ),
)

EXPERIMENT_CASES = (
    {
        "id": "renderTermCrossRepository",
        "expectSelection": True,
        "training": {
            "before": "ref: forwardRef 렌더 함수에서 두 번째 인자로 받은 ref입니다.",
            "after": "ref: forwardRef 렌더링 함수에서 두 번째 인자로 받은 ref입니다.",
            "source": {
                "repository": "reactKo",
                "commit": "8b5a2fcda780d6765d73ad1ae73cacb03caa18cf",
                "path": "src/content/reference/react/useImperativeHandle.md",
                "license": "CC-BY-4.0",
            },
        },
        "holdout": {
            "before": "이제 렌더 결과는 2가 됩니다.",
            "after": "이제 렌더링 결과는 2가 됩니다.",
            "source": {
                "repository": "vueKo",
                "commit": "b1de392776ea7cbcfa88381871193dd635b6d071",
                "path": "src/guide/essentials/reactivity-fundamentals.md",
                "license": "CC-BY-4.0",
            },
        },
    },
    {
        "id": "severalSpacingCrossRepository",
        "expectSelection": True,
        "training": {
            "before": "이벤트 핸들러를 작성하는 여러가지 방법",
            "after": "이벤트 핸들러를 작성하는 여러 가지 방법",
            "source": {
                "repository": "reactKo",
                "commit": "33209eac628f84054a4e00897760961cb9533b67",
                "path": "src/content/learn/responding-to-events.md",
                "license": "CC-BY-4.0",
            },
        },
        "holdout": {
            "before": "여러가지 타입이 가능하기 때문에 우리가 타입을 명시해야 하는 때와 비슷합니다.",
            "after": "여러 가지 타입이 가능하기 때문에 우리가 타입을 명시해야 하는 때와 비슷합니다.",
            "source": {
                "repository": "rustKo",
                "commit": "810f66f0ff211eb87d50090e521c0aa3b91085aa",
                "path": "second-edition/src/ch10-03-lifetime-syntax.md",
                "license": "MIT OR Apache-2.0",
            },
        },
    },
    {
        "id": "amongSpacingCrossRepository",
        "expectSelection": True,
        "training": {
            "before": "이 문제를 해결하는 올바른 방법은 여러 가지가 있는데, 그 중 한 가지 해결책을 소개합니다.",
            "after": "이 문제를 해결하는 올바른 방법은 여러 가지가 있는데, 그중 한 가지 해결책을 소개합니다.",
            "source": {
                "repository": "reactKo",
                "commit": "7e2f8f00ac9eef73203c7c368fbd53b70213bef7",
                "path": "src/content/learn/removing-effect-dependencies.md",
                "license": "CC-BY-4.0",
            },
        },
        "holdout": {
            "before": (
                "만일 여러 개의 입력 라이프타임 파라미터가 있는데, 메소드라서 그 중 하나가 &self 혹은 "
                "&mut self라고 한다면, self의 라이프타임이 모든 출력 라이프타임 파라미터에 대입됩니다."
            ),
            "after": (
                "만일 여러 개의 입력 라이프타임 파라미터가 있는데, 메소드라서 그중 하나가 &self 혹은 "
                "&mut self라고 한다면, self의 라이프타임이 모든 출력 라이프타임 파라미터에 대입됩니다."
            ),
            "source": {
                "repository": "rustKo",
                "commit": "810f66f0ff211eb87d50090e521c0aa3b91085aa",
                "path": "second-edition/src/ch10-03-lifetime-syntax.md",
                "license": "MIT OR Apache-2.0",
            },
        },
    },
    {
        "id": "colonPeriodCrossRepository",
        "expectSelection": True,
        "training": {
            "before": "이 비반응 로직을 Effect 이벤트로 옮기면 됩니다:",
            "after": "이 비반응 로직을 Effect 이벤트로 옮기면 됩니다.",
            "source": {
                "repository": "reactKo",
                "commit": "7e2f8f00ac9eef73203c7c368fbd53b70213bef7",
                "path": "src/content/learn/removing-effect-dependencies.md",
                "license": "CC-BY-4.0",
            },
        },
        "holdout": {
            "before": "String 타입의 값을 갖게 됩니다:",
            "after": "String 타입의 값을 갖게 됩니다.",
            "source": {
                "repository": "rustKo",
                "commit": "2987348d0b85bbd91a2b7267e5d050ffe33d7ce7",
                "path": "second-edition/src/ch06-01-defining-an-enum.md",
                "license": "MIT OR Apache-2.0",
            },
        },
    },
    {
        "id": "deicticMeaningAbstention",
        "expectSelection": False,
        "training": {
            "before": "이것은 리렌더링 간에 roomId가 같다면 createOptions 함수는 같다는 것을 보장합니다.",
            "after": "이는 리렌더링 간에 roomId가 같다면 createOptions 함수는 같다는 것을 보장합니다.",
            "source": {
                "repository": "reactKo",
                "commit": "8f3768f25c1561594725b2877d16f14775c65a00",
                "path": "src/content/reference/react/useCallback.md",
                "license": "CC-BY-4.0",
            },
        },
        "holdout": {
            "before": "이것은 다음과 같은 부분을 가진 독립적인 단위입니다:",
            "after": "이 컴포넌트는 다음과 같은 부분으로 이루어진 독립적인 단위입니다:",
            "source": {
                "repository": "vueKo",
                "commit": "b1de392776ea7cbcfa88381871193dd635b6d071",
                "path": "src/guide/scaling-up/state-management.md",
                "license": "CC-BY-4.0",
            },
        },
    },
    {
        "id": "passiveMeaningAbstention",
        "expectSelection": False,
        "training": {
            "before": "실제로 렌더링할 컴포넌트는 is prop에 의해 결정됩니다.",
            "after": "실제로 렌더링할 컴포넌트는 is prop에 따라 결정됩니다.",
            "source": {
                "repository": "vueKo",
                "commit": "b1de392776ea7cbcfa88381871193dd635b6d071",
                "path": "src/api/built-in-special-elements.md",
                "license": "CC-BY-4.0",
            },
        },
        "holdout": {
            "before": (
                "요소는 toLocaleString 메서드를 사용하여 문자열로 변환되고 이 문자열은 locale 고유 문자열에 의해 분리됩니다."
            ),
            "after": (
                "각 요소는 자체 toLocaleString 메서드를 사용하여 문자열로 변환되며, 이러한 문자열은 "
                "로케일별 구분 문자열로 분리됩니다."
            ),
            "source": {
                "repository": "mdnKo",
                "commit": "742d9a9829df079fc9de3096cfac245344ce1bc3",
                "path": "files/ko/web/javascript/reference/global_objects/array/tolocalestring/index.md",
                "license": "CC-BY-SA-2.5",
            },
        },
    },
    {
        "id": "wordBoundaryAbstention",
        "expectSelection": False,
        "training": {
            "before": "ref: forwardRef 렌더 함수에서 두 번째 인자로 받은 ref입니다.",
            "after": "ref: forwardRef 렌더링 함수에서 두 번째 인자로 받은 ref입니다.",
            "source": {
                "repository": "reactKo",
                "commit": "8b5a2fcda780d6765d73ad1ae73cacb03caa18cf",
                "path": "src/content/reference/react/useImperativeHandle.md",
                "license": "CC-BY-4.0",
            },
        },
        "holdout": {
            "before": "첫 번째 렌더링 중에 useRef는 { current: initialValue }을 반환합니다.",
            "after": "첫 번째 렌더링 중에 useRef는 { current: initialValue }을 반환합니다.",
            "source": {
                "repository": "reactKo",
                "commit": "b959fb7da1b6f1a76573cb5a5ad0a3a52e0ffeeb",
                "path": "src/content/learn/referencing-values-with-refs.md",
                "license": "CC-BY-4.0",
            },
        },
    },
)


@dataclass(frozen=True)
class Commit:
    sha: str
    date: str
    subject: str


@dataclass(frozen=True)
class Edit:
    repository: str
    commit: str
    date: str
    subject: str
    path: str
    before: str
    after: str
    similarity: float
    protectedAtoms: tuple[str, ...]
    factsPreserved: bool
    beforeFragment: str
    afterFragment: str
    fragmentOccurrences: int
    operationEligible: bool
    surfaceEligible: bool
    rulesResolved: tuple[str, ...]
    contentChangeSignal: bool


@dataclass(frozen=True)
class SurfaceOperation:
    before: str
    after: str

    def asDict(self) -> dict:
        return {"kind": "surfaceSubstitution", "before": self.before, "after": self.after}


def runGit(repository: Path, arguments: list[str]) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout


def correctionCommits(repository: Path, maximum: int) -> tuple[list[Commit], int]:
    """NUL로 커밋을 나눈다. 실제 Kubernetes 이력에는 제목 안 CR 때문에 splitlines가 쪼개지는 기록이 있다."""
    output = runGit(repository, ["log", "--no-merges", "--format=%H%x09%aI%x09%s%x00"])
    commits = []
    malformed = 0
    for record in output.split("\0"):
        record = record.strip("\r\n")
        if not record:
            continue
        parts = record.split("\t", 2)
        if len(parts) != 3:
            malformed += 1
            continue
        sha, date, subject = parts
        subject = SPACE.sub(" ", subject).strip()
        if CORRECTION.search(subject):
            commits.append(Commit(sha, date, subject))
        if len(commits) >= maximum:
            break
    return commits, malformed


def changedLinePairs(diff: str) -> list[tuple[str, str, str]]:
    """unified=0 diff의 한 hunk 안에서 일대일로 바뀐 줄만 돌려준다."""
    path = ""
    removed: list[str] = []
    added: list[str] = []
    pairs: list[tuple[str, str, str]] = []

    def flush() -> None:
        if path and len(removed) == len(added):
            pairs.extend((path, before, after) for before, after in zip(removed, added, strict=True))
        removed.clear()
        added.clear()

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            flush()
            path = ""
        elif line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("@@"):
            flush()
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    flush()
    return pairs


def prose(text: str) -> str:
    stripped = MARKDOWN_PREFIX.sub("", text.strip())
    return SPACE.sub(" ", plainText(stripped)).strip()


def sentencePairs(beforeLine: str, afterLine: str) -> list[tuple[str, str]]:
    beforeText = prose(beforeLine)
    afterText = prose(afterLine)
    if not KOREAN.search(beforeText) or not KOREAN.search(afterText):
        return []
    beforeSentences = splitSentences(beforeText)
    afterSentences = splitSentences(afterText)
    if len(beforeSentences) != len(afterSentences) or not beforeSentences:
        return []
    return [
        (before.text, after.text)
        for before, after in zip(beforeSentences, afterSentences, strict=True)
        if before.text != after.text and 8 <= len(before.text) <= 600 and 8 <= len(after.text) <= 600
    ]


def surfaceOperation(before: str, after: str) -> SurfaceOperation | None:
    """뜻을 추측하지 않아도 되는 공백, 문장부호, 한 글자 이내 표면 치환만 연산으로 인정한다."""
    operation = operationFromApproval(before, after)
    return SurfaceOperation(operation.before, operation.after) if operation else None


def applySurfaceOperation(text: str, operation: SurfaceOperation) -> str | None:
    """단어 경계를 지킨 한 자리에서만 치환하고 보호 원자가 달라지면 기권한다."""
    return applyOperation(text, ProductSurfaceOperation(operation.before, operation.after, ()))


def resolvedRules(before: str, after: str) -> tuple[str, ...]:
    return tuple(sorted({candidate.rule for candidate in learnText(before, after, Config(preset="docs"))}))


def editOf(repository: Repository, commit: Commit, path: str, before: str, after: str) -> Edit:
    similarity = SequenceMatcher(None, before, after, autojunk=False).ratio()
    beforeAtoms = protectedAtoms(before)
    afterAtoms = protectedAtoms(after)
    factsPreserved = beforeAtoms == afterAtoms
    beforeFragment, afterFragment = changedFragment(before, after)
    occurrences = before.count(beforeFragment) if beforeFragment else 0
    surface = surfaceOperation(before, after)
    eligible = (
        factsPreserved
        and similarity >= 0.62
        and bool(beforeFragment)
        and bool(afterFragment)
        and beforeFragment != afterFragment
        and len(beforeFragment) <= 80
        and len(afterFragment) <= 80
        and occurrences == 1
    )
    return Edit(
        repository=repository.id,
        commit=commit.sha,
        date=commit.date,
        subject=commit.subject,
        path=path,
        before=before,
        after=after,
        similarity=round(similarity, 6),
        protectedAtoms=beforeAtoms if factsPreserved else (),
        factsPreserved=factsPreserved,
        beforeFragment=beforeFragment,
        afterFragment=afterFragment,
        fragmentOccurrences=occurrences,
        operationEligible=eligible,
        surfaceEligible=surface is not None,
        rulesResolved=resolvedRules(before, after),
        contentChangeSignal=bool(CONTENT_CHANGE.search(commit.subject)),
    )


def harvestRepository(root: Path, repository: Repository, maximum: int) -> tuple[dict, list[Edit]]:
    checkout = root / repository.id
    if not checkout.is_dir():
        raise FileNotFoundError(f"저장소 사본이 없다: {checkout}")
    head = runGit(checkout, ["rev-parse", "HEAD"]).strip()
    commits, malformedCommits = correctionCommits(checkout, maximum)
    edits: list[Edit] = []
    seen: set[tuple[str, str, str, str]] = set()
    for offset, commit in enumerate(commits, start=1):
        diff = runGit(
            checkout,
            [
                "show",
                "--format=",
                "--unified=0",
                "--no-renames",
                "--diff-filter=M",
                commit.sha,
                "--",
                *repository.pathspecs,
            ],
        )
        for path, beforeLine, afterLine in changedLinePairs(diff):
            for before, after in sentencePairs(beforeLine, afterLine):
                key = (commit.sha, path, before, after)
                if key in seen:
                    continue
                seen.add(key)
                edits.append(editOf(repository, commit, path, before, after))
        if offset % 25 == 0:
            print(f"{repository.id}: 교정 커밋 {offset}/{len(commits)}, 문장 짝 {len(edits)}", flush=True)
    metadata = {
        **asdict(repository),
        "head": head,
        "correctionCommits": len(commits),
        "malformedCommits": malformedCommits,
        "sentencePairs": len(edits),
    }
    return metadata, edits


def operationGroups(edits: list[Edit]) -> list[dict]:
    groups: dict[tuple[str, str], list[Edit]] = {}
    for edit in edits:
        if edit.surfaceEligible and not edit.contentChangeSignal:
            groups.setdefault((edit.beforeFragment, edit.afterFragment), []).append(edit)
    result = []
    for (beforeFragment, afterFragment), found in groups.items():
        repositories = sorted({edit.repository for edit in found})
        commits = sorted({edit.commit for edit in found})
        if len(found) < 2:
            continue
        result.append(
            {
                "beforeFragment": beforeFragment,
                "afterFragment": afterFragment,
                "edits": len(found),
                "repositories": repositories,
                "commits": commits,
                "rules": sorted({rule for edit in found for rule in edit.rulesResolved}),
                "examples": [
                    {
                        "repository": edit.repository,
                        "commit": edit.commit,
                        "path": edit.path,
                        "before": edit.before,
                        "after": edit.after,
                    }
                    for edit in found[:5]
                ],
            }
        )
    return sorted(result, key=lambda item: (-len(item["repositories"]), -item["edits"], item["beforeFragment"]))


def reportData(metadata: list[dict], edits: list[Edit]) -> dict:
    summary = Counter()
    for edit in edits:
        summary["sentencePairs"] += 1
        summary["factsPreserved"] += edit.factsPreserved
        summary["operationEligible"] += edit.operationEligible
        summary["surfaceEligible"] += edit.surfaceEligible
        summary["resolvedByHanlint"] += bool(edit.rulesResolved)
        summary["eligibleAndResolved"] += edit.operationEligible and bool(edit.rulesResolved)
        summary["contentChangeSignal"] += edit.contentChangeSignal
    return {
        "version": 1,
        "experiment": "operationMemoryHarvest",
        "repositories": metadata,
        "filters": {
            "correctionSubject": CORRECTION.pattern,
            "contentChangeSubject": CONTENT_CHANGE.pattern,
            "minimumSimilarity": 0.62,
            "maximumFragmentCharacters": 80,
            "protectedAtomKinds": ["url", "number", "latin", "path", "code", "link"],
        },
        "summary": dict(summary),
        "operationGroups": operationGroups(edits),
        "edits": [asdict(edit) for edit in edits],
    }


def harvest(root: Path, maximum: int, repositoryIds: tuple[str, ...] = ()) -> dict:
    metadata = []
    edits = []
    for repository in REPOSITORIES:
        if repositoryIds and repository.id not in repositoryIds:
            continue
        repoMetadata, repoEdits = harvestRepository(root, repository, maximum)
        metadata.append(repoMetadata)
        edits.extend(repoEdits)
    return reportData(metadata, edits)


def combinedHarvest(paths: list[Path]) -> dict:
    repositoryById = {repository.id: repository for repository in REPOSITORIES}
    metadataById: dict[str, dict] = {}
    edits: list[Edit] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for metadata in data["repositories"]:
            previous = metadataById.get(metadata["id"])
            if previous is None or metadata["sentencePairs"] > previous["sentencePairs"]:
                metadataById[metadata["id"]] = metadata
        for raw in data["edits"]:
            key = (raw["repository"], raw["commit"], raw["path"], raw["before"], raw["after"])
            if key in seen:
                continue
            seen.add(key)
            repository = repositoryById[raw["repository"]]
            commit = Commit(raw["commit"], raw["date"], raw["subject"])
            edits.append(editOf(repository, commit, raw["path"], raw["before"], raw["after"]))
    return reportData([metadataById[key] for key in sorted(metadataById)], edits)


def operationPrompt(task: dict, exemplar: dict | None = None) -> str:
    lines = [
        "한국어 문장 하나를 교정한다.",
        "원문의 뜻, 사실, 수치, 고유명사, 코드와 조건을 보존한다.",
        "표기, 띄어쓰기, 프로젝트 용어 또는 문장부호에서 확실한 한 곳만 최소한으로 고친다.",
        "확실하게 고칠 수 없으면 원문을 그대로 출력한다.",
        "설명과 따옴표 없이 문장만 출력한다.",
    ]
    if exemplar:
        lines.extend(
            [
                "다른 문장에서 글쓴이가 승인한 본보기:",
                "본보기의 사실은 옮기지 않고 같은 표면 고침이 필요할 때만 참고한다.",
                f"전: {exemplar['before']}",
                f"후: {exemplar['after']}",
            ]
        )
    lines.append(f"교정할 문장: {task['sentence']}")
    return "\n".join(lines)


def prepareOperationExperiment(harvestPath: Path) -> dict:
    harvestData = readJson(harvestPath)
    repositoryMetadata = {item["id"]: item for item in harvestData["repositories"]}
    tasks = []
    for case in EXPERIMENT_CASES:
        training = case["training"]
        holdout = case["holdout"]
        for source in (training["source"], holdout["source"]):
            metadata = repositoryMetadata.get(source["repository"])
            if metadata is None or metadata["license"] != source["license"]:
                raise ValueError(f"자료원 메타데이터가 맞지 않는다: {source['repository']}")
        operation = surfaceOperation(training["before"], training["after"])
        operationOutput = applySurfaceOperation(holdout["before"], operation) if operation else None
        selected = operationOutput is not None
        if selected != case["expectSelection"]:
            raise ValueError(f"고정 과제 선택 기대와 다르다: {case['id']} expected={case['expectSelection']} actual={selected}")
        task = {
            "id": case["id"],
            "kind": "positive" if case["expectSelection"] else "abstention",
            "sentence": holdout["before"],
            "approvedAfter": holdout["after"],
            "training": training,
            "holdoutSource": holdout["source"],
            "operation": operation.asDict() if operation else None,
            "operationSelected": selected,
            "operationOutput": operationOutput,
            "selectionReason": (
                "표면 서명과 단어 경계, 보호 원자가 모두 맞음"
                if selected
                else "표면 서명이 뜻 추론을 요구하거나 목표 단어 경계와 맞지 않아 기권"
            ),
        }
        reasonPrompt = operationPrompt(task)
        task["prompts"] = {
            "reasonOnly": reasonPrompt,
            "blindExemplar": operationPrompt(task, training),
            "exactReplay": reasonPrompt,
            "operationPatch": reasonPrompt,
        }
        tasks.append(task)
    return {
        "version": 1,
        "experiment": "surfaceOperationMemory",
        "harvest": {
            "path": str(harvestPath),
            "sha256": fileSha256(harvestPath),
            "repositories": [
                {
                    "id": item["id"],
                    "repo": item["repo"],
                    "license": item["license"],
                    "licensePath": item["licensePath"],
                    "head": item["head"],
                    "sentencePairs": item["sentencePairs"],
                }
                for item in harvestData["repositories"]
            ],
        },
        "selection": {
            "kind": "surfaceSubstitution",
            "maximumFragmentCharacters": 32,
            "maximumSurfaceEditDistance": 1,
            "guards": [
                "한글, 영문, 숫자를 제외한 공백과 문장부호를 눕힌 표면 편집 거리 1 이하",
                "지시어 조각 제외",
                "숫자, URL, 라틴 식별자, 경로, 코드, 링크 목적지 보존",
                "목표 문장의 단어 경계에서 유일한 한 자리",
            ],
        },
        "conditions": list(EXPERIMENT_CONDITIONS),
        "tasks": tasks,
    }


def runOperationExperiment(
    manifest: dict,
    model: str,
    endpoint: str,
    timeout: int,
    checkpoint: Path | None,
) -> dict:
    responses = []
    cache: dict[str, tuple[str, dict, str]] = {}
    runner = {
        "kind": "ollama",
        "endpoint": endpoint,
        "model": ollamaInfo(endpoint, model, timeout),
        "think": False,
        "options": OLLAMA_OPTIONS,
    }
    modelPrompts = {prompt for task in manifest["tasks"] for prompt in task["prompts"].values()}
    total = len(manifest["tasks"]) * len(EXPERIMENT_CONDITIONS)
    for task in manifest["tasks"]:
        for condition in EXPERIMENT_CONDITIONS:
            directOutput = None
            directKind = None
            if condition == "exactReplay" and task["sentence"] == task["training"]["before"]:
                directOutput = task["training"]["after"]
                directKind = "exactReplay"
            elif condition == "operationPatch" and task["operationSelected"]:
                directOutput = task["operationOutput"]
                directKind = "surfaceOperation"
            prompt = task["prompts"][condition]
            promptHash = hashlib.sha256(prompt.encode()).hexdigest()
            if directOutput is not None:
                item = {
                    "taskId": task["id"],
                    "condition": condition,
                    "output": directOutput,
                    "metrics": {"direct": directKind},
                    "promptSha256": promptHash,
                }
            elif promptHash in cache:
                output, metrics, reusedFrom = cache[promptHash]
                item = {
                    "taskId": task["id"],
                    "condition": condition,
                    "output": output,
                    "metrics": metrics,
                    "promptSha256": promptHash,
                    "reusedFrom": reusedFrom,
                }
            else:
                output, metrics = ollamaGenerate(prompt, model, endpoint, timeout)
                reusedFrom = f"{task['id']}:{condition}"
                cache[promptHash] = (output, metrics, reusedFrom)
                item = {
                    "taskId": task["id"],
                    "condition": condition,
                    "output": output,
                    "metrics": metrics,
                    "promptSha256": promptHash,
                }
            responses.append(item)
            partial = {
                "version": 1,
                "complete": False,
                "uniquePrompts": len(modelPrompts),
                "runner": runner,
                "responses": responses,
            }
            if checkpoint:
                writeJson(checkpoint, partial)
            print(f"응답 {len(responses)}/{total}: {task['id']} {condition}", flush=True)
    return {
        "version": 1,
        "complete": True,
        "uniquePrompts": len(modelPrompts),
        "runner": runner,
        "responses": responses,
    }


def operationJudgmentTemplate(manifest: dict, responses: dict) -> dict:
    tasks = {task["id"]: task for task in manifest["tasks"]}
    return {
        "version": 1,
        "instructions": (
            "원문 사실과 뜻을 보존했는지와, 승인 후와 꼭 같지 않아도 해당 표기 문제를 올바르게 고쳤는지를 각각 판정한다."
        ),
        "judgments": [
            {
                "taskId": response["taskId"],
                "condition": response["condition"],
                "sentence": tasks[response["taskId"]]["sentence"],
                "approvedAfter": tasks[response["taskId"]]["approvedAfter"],
                "output": response["output"],
                "meaningPreserved": None,
                "acceptable": None,
                "note": "",
            }
            for response in responses["responses"]
        ],
    }


def applyOperationJudgments(responses: dict, judgments: dict) -> dict:
    labels = {}
    for item in judgments["judgments"]:
        conditions = EXPERIMENT_CONDITIONS if item["condition"] == "*" else (item["condition"],)
        for condition in conditions:
            labels[(item["taskId"], condition)] = item
    expected = {(item["taskId"], item["condition"]) for item in responses["responses"]}
    if labels.keys() != expected:
        raise ValueError(f"판정 키가 맞지 않는다: 빠짐 {len(expected - labels.keys())}, 모름 {len(labels.keys() - expected)}")
    merged = []
    for response in responses["responses"]:
        label = labels[(response["taskId"], response["condition"])]
        if not isinstance(label.get("meaningPreserved"), bool) or not isinstance(label.get("acceptable"), bool):
            raise ValueError(f"판정이 비었다: {response['taskId']} {response['condition']}")
        merged.append(
            {
                **response,
                "meaningPreserved": label["meaningPreserved"],
                "acceptable": label["acceptable"],
                "judgmentNote": label.get("note", ""),
            }
        )
    return {**responses, "responses": merged}


def normalizedSentence(text: str) -> str:
    return SPACE.sub(" ", text).strip()


def scoredOperationExperiment(manifest: dict, responses: dict) -> tuple[str, dict]:
    tasks = {task["id"]: task for task in manifest["tasks"]}
    results = []
    for response in responses["responses"]:
        task = tasks[response["taskId"]]
        protected = protectedAtoms(task["sentence"]) == protectedAtoms(response["output"])
        approvedMatch = normalizedSentence(response["output"]) == normalizedSentence(task["approvedAfter"])
        result = {
            "taskId": task["id"],
            "condition": response["condition"],
            "kind": task["kind"],
            "operationSelected": task["operationSelected"],
            "approvedMatch": approvedMatch,
            "protectedFacts": protected,
            "meaningPreserved": response["meaningPreserved"],
            "acceptable": response["acceptable"],
        }
        result["safeSuccess"] = protected and result["meaningPreserved"] and result["acceptable"]
        results.append(result)
    lines = [f"과제 {len(tasks)}개, 모델 호출 {responses['uniquePrompts']}회", "", "조건별"]
    summary = {}
    for condition in EXPERIMENT_CONDITIONS:
        chosen = [result for result in results if result["condition"] == condition]
        values = {
            "tasks": len(chosen),
            "approvedMatch": sum(result["approvedMatch"] for result in chosen),
            "protectedFacts": sum(result["protectedFacts"] for result in chosen),
            "meaningPreserved": sum(result["meaningPreserved"] for result in chosen),
            "acceptable": sum(result["acceptable"] for result in chosen),
            "safeSuccess": sum(result["safeSuccess"] for result in chosen),
        }
        summary[condition] = values
        lines.append(
            f"  {condition:15} 승인문 일치 {values['approvedMatch']}/{values['tasks']}, "
            f"보호 원자 {values['protectedFacts']}/{values['tasks']}, 뜻 보존 {values['meaningPreserved']}/{values['tasks']}, "
            f"안전 성공 {values['safeSuccess']}/{values['tasks']}"
        )
    lines.extend(["", "operationPatch 짝 비교"])
    byKey = {(result["taskId"], result["condition"]): result for result in results}
    pairSummary = {}
    for baseline in ("reasonOnly", "blindExemplar", "exactReplay"):
        pairs = [(byKey[(taskId, baseline)], byKey[(taskId, "operationPatch")]) for taskId in tasks]
        operationWins = sum(not base["safeSuccess"] and operation["safeSuccess"] for base, operation in pairs)
        baselineWins = sum(base["safeSuccess"] and not operation["safeSuccess"] for base, operation in pairs)
        ties = len(pairs) - operationWins - baselineWins
        pairSummary[baseline] = {
            "operationWins": operationWins,
            "baselineWins": baselineWins,
            "ties": ties,
        }
        lines.append(f"  {baseline:15} 연산만 성공 {operationWins}, 기준만 성공 {baselineWins}, 같은 결과 {ties}")
    selectedIds = [task["id"] for task in tasks.values() if task["operationSelected"]]
    selectedPairs = [(byKey[(taskId, "exactReplay")], byKey[(taskId, "operationPatch")]) for taskId in selectedIds]
    selectedSummary = {
        "tasks": len(selectedPairs),
        "operationWins": sum(not base["safeSuccess"] and operation["safeSuccess"] for base, operation in selectedPairs),
        "exactWins": sum(base["safeSuccess"] and not operation["safeSuccess"] for base, operation in selectedPairs),
    }
    selectedSummary["ties"] = len(selectedPairs) - selectedSummary["operationWins"] - selectedSummary["exactWins"]
    lines.append(
        f"  선택된 {len(selectedPairs)}과제 연산만 성공 {selectedSummary['operationWins']}, "
        f"exact만 성공 {selectedSummary['exactWins']}, 같은 결과 {selectedSummary['ties']}"
    )
    return "\n".join(lines), {
        "version": 1,
        "summary": summary,
        "pairSummary": pairSummary,
        "selectedSummary": selectedSummary,
        "results": results,
    }


def writeJson(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fileSha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selfTest() -> None:
    assert sentencePairs("문장을 고쳐 쓰도록 합니다.", "문장을 고쳐 씁니다.") == [
        ("문장을 고쳐 쓰도록 합니다.", "문장을 고쳐 씁니다.")
    ]
    before = "결과를 output.json에 3번 저장합니다."
    after = "결과를 output.json에 4번 저장합니다."
    assert protectedAtoms(before) != protectedAtoms(after)
    assert changedFragment("이것은은 DOM 노드입니다.", "이것은 DOM 노드입니다.") == ("이것은은", "이것은")
    assert changedFragment("출력 됩니다.", "출력됩니다.") == ("출력 됩니다", "출력됩니다")
    render = surfaceOperation("첫 렌더 중에 객체를 만듭니다.", "첫 렌더링 중에 객체를 만듭니다.")
    assert render == SurfaceOperation("렌더", "렌더링")
    assert applySurfaceOperation("다음 렌더 중에 객체를 만듭니다.", render) == "다음 렌더링 중에 객체를 만듭니다."
    assert applySurfaceOperation("다음 렌더링 중에 객체를 만듭니다.", render) is None
    assert applySurfaceOperation("`렌더` 결과입니다.", render) is None
    assert surfaceOperation("이것은 단위입니다.", "이는 단위입니다.") is None
    assert surfaceOperation("값은 3입니다.", "값은 4입니다.") is None
    assert surfaceOperation("값은 useState입니다.", "값은 useRef입니다.") is None


def parseArgs(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="공개 Git 교정 이력에서 편집 연산 후보를 채굴한다")
    subparsers = parser.add_subparsers(dest="command", required=True)
    harvestParser = subparsers.add_parser("harvest")
    harvestParser.add_argument("root", type=Path)
    harvestParser.add_argument("--maximum-commits", dest="maximumCommits", type=int, default=250)
    harvestParser.add_argument(
        "--repository",
        dest="repositories",
        action="append",
        choices=tuple(repository.id for repository in REPOSITORIES),
        default=[],
    )
    harvestParser.add_argument("--output", type=Path, required=True)
    combineParser = subparsers.add_parser("combine")
    combineParser.add_argument("inputs", nargs="+", type=Path)
    combineParser.add_argument("--output", type=Path, required=True)
    prepareParser = subparsers.add_parser("prepare-experiment")
    prepareParser.add_argument("harvest", type=Path)
    prepareParser.add_argument("--output", type=Path, required=True)
    runParser = subparsers.add_parser("run-experiment")
    runParser.add_argument("manifest", type=Path)
    runParser.add_argument("--ollama-model", dest="ollamaModel", required=True)
    runParser.add_argument("--ollama-endpoint", dest="ollamaEndpoint", default=OLLAMA_ENDPOINT)
    runParser.add_argument("--timeout", type=int, default=120)
    runParser.add_argument("--output", type=Path, required=True)
    judgmentParser = subparsers.add_parser("judgment-template")
    judgmentParser.add_argument("manifest", type=Path)
    judgmentParser.add_argument("responses", type=Path)
    judgmentParser.add_argument("--output", type=Path, required=True)
    scoreParser = subparsers.add_parser("score-experiment")
    scoreParser.add_argument("manifest", type=Path)
    scoreParser.add_argument("responses", type=Path)
    scoreParser.add_argument("--judgments", type=Path, required=True)
    scoreParser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    selfTest()
    args = parseArgs(argv)
    if args.command == "harvest":
        data = harvest(args.root.resolve(), args.maximumCommits, tuple(args.repositories))
        writeJson(args.output, data)
        print(json.dumps(data["summary"], ensure_ascii=False, indent=2))
        print(f"연산 그룹 {len(data['operationGroups'])}개")
    elif args.command == "combine":
        data = combinedHarvest(args.inputs)
        writeJson(args.output, data)
        print(json.dumps(data["summary"], ensure_ascii=False, indent=2))
        print(f"연산 그룹 {len(data['operationGroups'])}개")
    elif args.command == "prepare-experiment":
        data = prepareOperationExperiment(args.harvest.resolve())
        writeJson(args.output, data)
        print(f"고정 보류 과제 {len(data['tasks'])}개를 {args.output}에 썼다")
    elif args.command == "run-experiment":
        data = runOperationExperiment(
            readJson(args.manifest),
            args.ollamaModel,
            args.ollamaEndpoint,
            args.timeout,
            args.output,
        )
        writeJson(args.output, data)
    elif args.command == "judgment-template":
        data = operationJudgmentTemplate(readJson(args.manifest), readJson(args.responses))
        writeJson(args.output, data)
        print(f"판정 틀을 {args.output}에 썼다")
    else:
        responses = applyOperationJudgments(readJson(args.responses), readJson(args.judgments))
        report, data = scoredOperationExperiment(readJson(args.manifest), responses)
        print(report)
        if args.output:
            writeJson(args.output, data)
    if not hasattr(args, "output") or args.output is None or not args.output.exists():
        return 0
    print(f"산출물 SHA256 {fileSha256(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
