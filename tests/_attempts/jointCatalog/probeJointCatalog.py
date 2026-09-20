"""jointCatalog. 말뭉치가 만든 닫힌 고침 목록이 채워지는지, 그 목록에서 고른 고침이 자유 고침보다 나은지 잰다.

**왜 통로를 바꾸나.** usageLift 가 네 번 재서 네 번 다 실패한 것은 용례를 프롬프트에 얹는 방식이었다 (300쌍, 두 모델,
세 조건, 부호검정 p 1.0000). 모델이 문장을 자유롭게 다시 쓰면 새 결합의 73%가 그 종류의 말뭉치에 없었고, 명사 쌓기를
풀다 `의` 사슬을 만들어 새 error 가 2건에서 10건이 됐다.

**바꾼 통로.** 모델에게 문장을 지으라 하지 않고 **말뭉치가 만든 닫힌 목록에서 고르라** 한다. 목록은 제품이 만든다
(`hanlint.edit.usageCandidates`). 여기서 그 코드를 그대로 불러 쓴다. 탐침이 제품과 다른 계산을 하면 잰 것이 제품이
아니게 된다.

**재는 것 둘.**
1. `census`: 채움률. 지적 가운데 후보가 하나라도 남는 비율. 0 에 가까우면 고를 것이 없어 방향이 성립하지 않는다.
   거르기가 실제로 몇 개를 쳐내는지 (규칙은 풀지만 다른 규칙을 늘리는 꼴) 를 함께 센다. 그 수가 0 이면 거르기는 장식이다.
2. `pick`: 고침의 질. 같은 문장을 두 통로로 고쳐 견준다. 사전 등록은 probeJointCatalog_log.md 가 소유한다.

```console
python -X utf8 -B tests/_attempts/jointCatalog/probeJointCatalog.py census --limit 300 --per-rule 200
python -X utf8 -B tests/_attempts/jointCatalog/probeJointCatalog.py show --limit 60 --per-rule 6
```
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from scripts.fetch.dartReports import defaultRoot, readCorpus  # noqa: E402

from hanlint import Config, lintText  # noqa: E402
from hanlint.analysis.grammar import fitJosa  # noqa: E402
from hanlint.analysis.tokenize import (  # noqa: E402
    EDGE_PUNCTUATION,
    genitiveSpans,
    isBareNoun,
    nounRuns,
    stripJosa,
    words,
)
from hanlint.document import parseMarkdown  # noqa: E402
from hanlint.fingerprint import buildFingerprint  # noqa: E402
from hanlint.rules import Candidate, runAll  # noqa: E402
from hanlint.usage import UsageIndex, defaultUsageRoot, loadIndex  # noqa: E402


def wordSpans(text: str) -> list[tuple[int, int]]:
    """어절마다 앞뒤 부호를 뺀 핵의 (시작, 끝) 글자 자리. words() 와 같은 차례다."""
    spans: list[tuple[int, int]] = []
    at = 0
    for raw in text.split():
        at = text.index(raw, at)
        end = at + len(raw)
        start = at
        while start < end and text[start] in EDGE_PUNCTUATION:
            start += 1
        while end > start and text[end - 1] in EDGE_PUNCTUATION:
            end -= 1
        spans.append((start, end))
        at += len(raw)
    return spans


# ---- 잰 대상. 2026-09-20 에 제품에서 되돌렸으므로 (실패했다) 탐침이 들고 있다. 되살리려면 커밋 dcb62a1 ----

JOINT_SAMPLE = 800
"""한 이음을 셀 때 읽을 문장 수 상한. 두 낱말이 함께 든 문장을 일정 간격으로 고르므로 조사의 상대 빈도는 치우치지
않는다. 문서 수는 이 표본 안의 수라 말뭉치 전체보다 작다. 있고 없고가 아니라 그 자리에 어느 조사가 흔한지를 묻는
자리라 표본으로 충분하다. 800 은 흔한 낱말 쌍 (교집합 1만 문장) 에서도 한 이음이 1초 안에 끝나는 크기다."""
MIN_JOINT_DOCUMENTS = 2
"""그 조사를 쓴 문서가 표본에서 몇 편 이상이어야 이음으로 보는가. 한 편은 한 회사의 버릇이다."""


@dataclass(frozen=True)
class Joint:
    particle: str
    """왼쪽 어절에 붙어 있던 조사. 빈 문자열이면 조사 없이 붙여 썼다는 뜻이다 (쌓은 꼴)."""
    documents: int
    """표본 안에서 그렇게 쓴 문서 수."""


def jointParticles(index: UsageIndex, left: str, right: str, sample: int = JOINT_SAMPLE) -> tuple[Joint, ...]:
    """두 어절 핵이 나란히 온 자리의 조사를 문서 수 내림차순으로. 빈 조사도 넣는다 (쌓은 꼴의 근거다)."""
    leftFound, rightFound = index.lookup(left), index.lookup(right)
    if not leftFound or not rightFound:
        return ()
    first = index.postingsAt(leftFound[1], leftFound[2])
    second = index.postingsAt(rightFound[1], rightFound[2])
    if len(first) > len(second):
        first, second = second, first
    other = {sentenceId for sentenceId, _ in second}
    shared = [sentenceId for sentenceId, _ in first if sentenceId in other]
    if not shared:
        return ()
    stride = max(1, len(shared) // sample)
    tally: dict[str, set[str]] = {}
    for sentenceId in shared[::stride][:sample]:
        _, source, text = index.sentence(sentenceId)
        found = words(text)
        for position in range(len(found) - 1):
            before, after = found[position], found[position + 1]
            if before.endsClause or before.particle or after.particle:
                continue
            if stripJosa(before.core) != left or stripJosa(after.core) != right:
                continue
            tally.setdefault(before.core[len(left) :], set()).add(source)
    ranked = sorted(tally.items(), key=lambda item: (-len(item[1]), item[0]))
    return tuple(Joint(particle, len(sources)) for particle, sources in ranked)


class Joints:
    """색인에 이음을 묻고 답을 기억한다. 한 글에서 같은 이음을 여러 지적이 묻는다."""

    def __init__(self, index: UsageIndex, sample: int = JOINT_SAMPLE, minimum: int = MIN_JOINT_DOCUMENTS) -> None:
        self.index = index
        self.sample = sample
        self.minimum = minimum
        self.queries = 0
        """색인을 실제로 읽은 횟수. 기억한 답을 다시 쓰면 늘지 않는다."""
        self._known: dict[tuple[str, str], tuple[Joint, ...]] = {}

    def particles(self, left: str, right: str) -> tuple[Joint, ...]:
        """문서 수가 minimum 편 이상인 이음. 빈 조사도 그대로 준다.

        빈 조사의 뜻은 쓰는 쪽에서 갈린다. 명사 쌓기에서는 원문이 이미 그 꼴이라 고침이 아니고, `의` 사슬에서는
        `의` 를 빼는 고침이다 (`이사회의 결의` -> `이사회 결의`). 여기서 거르면 그 고침이 사라진다.
        """
        key = (left, right)
        if key not in self._known:
            self.queries += 1
            self._known[key] = jointParticles(self.index, left, right, self.sample)
        return tuple(joint for joint in self._known[key] if joint.documents >= self.minimum)


JOINT_RULES = ("nounPile", "euiChain")
"""이음으로 고칠 수 있는 규칙. 둘 다 고치기가 조사 하나를 넣거나 바꾸는 일이다."""
MAX_CANDIDATES = 6
"""한 지적에 실을 후보 수 상한. 고르는 쪽이 한눈에 읽을 크기다. 등수가 아니라 근거 문서 수 내림차순의 앞부분이다."""
MAX_SLOTS = 10
"""한 문장에서 볼 자리 수 상한. 근거가 많은 차례로 앞에서 자른다.

자리가 이보다 많은 문장은 조사를 끼워 고칠 문장이 아니라 다시 쓸 문장이다. 상한이 없으면 사업보고서의 긴 한 문장
(`의` 자리 수십 개) 이 후보 수백 개를 만들고, 후보마다 검사를 다시 도느라 글 하나가 분 단위로 늘어진다."""


@dataclass(frozen=True)
class Slot:
    """고칠 수 있는 한 자리. 말뭉치가 그 자리에 쓴 조사 하나가 자리 하나다."""

    at: int
    stop: int
    """[at, stop) 을 particle 로 바꾼다. 넣기만 할 때는 둘이 같다."""
    particle: str
    documents: int
    """그 조사를 쓴 글의 수. 근거지 등수가 아니다."""
    why: str


def applyEdits(text: str, slots: list[Slot]) -> str:
    """자리들을 뒤에서부터 적용한다. 앞을 먼저 고치면 뒤 자리가 밀린다."""
    for slot in sorted(slots, key=lambda one: -one.at):
        text = text[: slot.at] + slot.particle + text[slot.stop :]
    return text


def jointWhy(left: str, joint: Joint, right: str) -> str:
    """후보의 근거 한 줄. 자기 도구가 검사하는 글이라 조사를 받침에 맞춘다."""
    shown = f"{left}{joint.particle} {right}"
    return f"`{shown}`{fitJosa(shown, '로')} 쓴 글 {joint.documents}편"


def chainBoundaries(text: str, minimum: int) -> list[int]:
    """임계 이상인 명사 연쇄 안의 어절 경계. words() 차례의 왼쪽 어절 index 다."""
    piles = {tuple(chain) for chain, length in nounRuns(text) if length >= minimum}
    if not piles:
        return []
    cores = [word.core for word in words(text)]
    places: set[int] = set()
    for chain in piles:
        for start in range(len(cores) - len(chain) + 1):
            if cores[start : start + len(chain)] == list(chain):
                places.update(range(start, start + len(chain) - 1))
    return sorted(places)


def nounPileSlots(text: str, joints: Joints, minimum: int) -> list[Slot]:
    """명사 쌓기 경계마다 넣을 수 있는 조사. 말뭉치가 붙여서만 쓰는 경계는 자리가 아니다."""
    spans = wordSpans(text)
    cores = [stripJosa(word.core) for word in words(text)]
    slots: list[Slot] = []
    for position in chainBoundaries(text, minimum):
        left, right = cores[position], cores[position + 1]
        at = spans[position][1]
        for joint in joints.particles(left, right):
            if not joint.particle:
                continue
            slots.append(Slot(at, at, joint.particle, joint.documents, jointWhy(left, joint, right)))
    return slots


def euiChainSlots(text: str, joints: Joints) -> list[Slot]:
    """`의` 자리마다 바꿔 넣을 수 있는 조사. 빈 조사는 `의` 를 빼는 고침이다."""
    spans = wordSpans(text)
    found = words(text)
    cores = [stripJosa(word.core) for word in found]
    starts = {span[0]: position for position, span in enumerate(spans)}
    slots: list[Slot] = []
    for start, end in genitiveSpans(text):
        position = starts.get(start)
        if position is None or position + 1 >= len(found) or not text[start:end].endswith("의"):
            continue
        left, right = cores[position], cores[position + 1]
        for joint in joints.particles(left, right):
            if joint.particle == "의":
                continue
            slots.append(Slot(end - 1, end, joint.particle, joint.documents, jointWhy(left, joint, right)))
    return slots


def slotCandidates(text: str, slots: list[Slot]) -> list[tuple[str, str]]:
    """자리 하나씩 고친 꼴과, 자리 여럿을 함께 고친 꼴.

    하나씩 고친 꼴을 근거가 많은 차례로 먼저 낸다 (같으면 원문에서 앞선 자리). 등수가 아니라 읽는 차례다.
    한 자리만 고쳐서는 안 풀리는 지적이 많아 (`의` 가 넷이면 하나 바꿔도 셋이다) 자리를 쌓은 꼴을 뒤에 붙인다.
    쌓는 쪽은 자리를 원문 차례대로 더할 뿐 조합을 다 펼치지 않고, 자리마다 그 자리에서 근거가 가장 많은 조사를 쓴다.
    """
    made: list[tuple[str, str]] = []
    seen = {text}
    for slot in sorted(slots, key=lambda one: (-one.documents, one.at, one.particle)):
        candidate = applyEdits(text, [slot])
        if candidate not in seen:
            seen.add(candidate)
            made.append((candidate, slot.why))
    best: dict[int, Slot] = {}
    for slot in sorted(slots, key=lambda one: (-one.documents, one.particle)):
        best.setdefault(slot.at, slot)
    ordered = [best[at] for at in sorted(best)]
    for count in range(2, len(ordered) + 1):
        chosen = ordered[:count]
        candidate = applyEdits(text, chosen)
        if candidate not in seen:
            seen.add(candidate)
            made.append((candidate, f"자리 {count}곳을 함께. " + " / ".join(slot.why for slot in chosen)))
    return made


def sentenceTally(text: str, config: Config) -> dict[str, int]:
    """규칙 이름별 지적 수. 한 문장만 넣으므로 문단과 문서 규칙은 돌지 않는다."""
    counts: dict[str, int] = {}
    for finding in runAll(buildFingerprint(parseMarkdown(text), config), config):
        counts[finding.rule] = counts.get(finding.rule, 0) + 1
    return counts


def keeps(candidate: str, rule: str, before: dict[str, int], config: Config) -> bool:
    """겨눈 규칙이 줄고 **다른 어떤 규칙도 늘지 않으면** 남는다. 고치다 새 결함을 만드는 길을 막는 자리다.

    error 총수로 보면 안 된다. 쌓기 하나가 사라지고 `의` 사슬 하나가 생기면 총수가 같아 그대로 남는다.
    그것이 실측에서 새 error 를 2건에서 10건으로 늘린 바로 그 꼴이다 (tests/_attempts/usageLift).
    notice 도 막는다. 지적은 지적이고, 여기서 둘을 갈라 예외를 두기 시작하면 목록이 늘어난다.
    """
    after = sentenceTally(candidate, config)
    if after.get(rule, 0) >= before.get(rule, 0):
        return False
    return all(count <= before.get(name, 0) for name, count in after.items())


def candidatesFor(text: str, rule: str, joints: Joints, config: Config, limit: int = MAX_CANDIDATES) -> tuple[Candidate, ...]:
    """한 문장의 한 규칙에 대한 닫힌 후보 목록. 말뭉치가 뒷받침하고 다시 검사해도 규칙이 풀리는 것만."""
    slots = nounPileSlots(text, joints, config.nounPileMin) if rule == "nounPile" else euiChainSlots(text, joints)
    slots = sorted(slots, key=lambda one: (-one.documents, one.at, one.particle))[:MAX_SLOTS]
    if not slots:
        return ()
    before = sentenceTally(text, config)
    kept = []
    for candidate, why in slotCandidates(text, slots):
        if len(kept) >= limit:
            break
        if keeps(candidate, rule, before, config):
            kept.append(Candidate(candidate, why))
    return tuple(kept)


SEED = 42
MAX_SENTENCE = 200
"""과제 문장의 글자 수 상한. 심판이 원문과 고침 셋을 한 화면에서 읽게 하려는 제한이다. 고르는 기준으로 미리 적었다."""
ARMS = ("free", "pick", "top")
KEEP = "원문 유지"
OLLAMA_OPTIONS = {"temperature": 0, "seed": SEED, "num_ctx": 8192}


def reportConfig() -> Config:
    """사업보고서 프리셋에 nounPile 을 error 로. scripts/measure/reports.py 와 같은 설정이다."""
    return Config(preset="report", enforceStyle=["nounPile"])


def sampleFindings(limit: int, perRule: int, config: Config) -> dict[str, list[str]]:
    """보고서에서 규칙마다 지적 문장을 고정 씨앗으로 고른다."""
    picked: dict[str, list[str]] = {rule: [] for rule in JOINT_RULES}
    for _, text in readCorpus(defaultRoot(), limit):
        for finding in lintText(text, config=config):
            if finding.rule in picked:
                picked[finding.rule].append(finding.quote)
    rng = random.Random(SEED)
    for rule in JOINT_RULES:
        rng.shuffle(picked[rule])
        picked[rule] = picked[rule][:perRule]
    return picked


def rawCandidates(text: str, rule: str, joints: Joints, config: Config) -> list[tuple[str, str]]:
    """거르기 전 후보. 제품이 쓰는 자리 계산을 그대로 쓰고 거르기만 뺀다."""
    slots = nounPileSlots(text, joints, config.nounPileMin) if rule == "nounPile" else euiChainSlots(text, joints)
    return slotCandidates(text, slots) if slots else []


def census(limit: int, perRule: int, kind: str) -> str:
    index = loadIndex(kind, defaultUsageRoot())
    if index is None:
        raise SystemExit(f"{kind} 색인이 없다. hanlint usage build 를 먼저 돌린다")
    config = reportConfig()
    joints = Joints(index)
    picked = sampleFindings(limit, perRule, config)

    lines = [f"보고서 {limit}편에서 규칙마다 {perRule}건 (씨앗 {SEED}), 근거 색인 {kind} 문서 {index.documents}편", ""]
    summary: dict[str, dict] = {}
    for rule in JOINT_RULES:
        started = time.time()
        raw = solved = broke = kept = withRaw = withKept = done = 0
        for sentence in picked[rule]:
            before = sentenceTally(sentence, config)
            made = rawCandidates(sentence, rule, joints, config)
            good = 0
            for candidate, _ in made:
                after = sentenceTally(candidate, config)
                if after.get(rule, 0) >= before.get(rule, 0):
                    continue
                solved += 1
                if all(count <= before.get(name, 0) for name, count in after.items()):
                    good += 1
                else:
                    broke += 1
            raw += len(made)
            kept += min(good, MAX_CANDIDATES)
            withRaw += bool(made)
            withKept += bool(good)
            done += 1
            if done % 25 == 0:
                print(f"  {rule} {done}/{len(picked[rule])} ({time.time() - started:.0f}초)", file=sys.stderr, flush=True)
        count = len(picked[rule])
        lines.append(f"{rule}  지적 {count}건, {time.time() - started:.0f}초")
        lines.append(f"  자리가 나온 지적 {withRaw}건 ({withRaw / count:.0%}), 거르기 전 후보 {raw}개")
        lines.append(f"  규칙을 푸는 후보 {solved}개. 그중 다른 규칙을 늘려 버린 것 {broke}개 (거르기가 쳐낸 수)")
        lines.append(f"  남은 후보 {kept}개, **채움률 {withKept}/{count} ({withKept / count:.0%})**")
        lines.append("")
        summary[rule] = {
            "findings": count,
            "raw": raw,
            "solved": solved,
            "broke": broke,
            "kept": kept,
            "withRaw": withRaw,
            "withKept": withKept,
        }
    print(json.dumps(summary, ensure_ascii=False), file=sys.stderr)
    return "\n".join(lines)


def show(limit: int, perRule: int, kind: str) -> str:
    """거른 뒤 남은 후보를 실물로 보인다. 수가 아니라 글을 본다."""
    index = loadIndex(kind, defaultUsageRoot())
    config = reportConfig()
    joints = Joints(index)
    picked = sampleFindings(limit, perRule * 20, config)
    lines: list[str] = []
    for rule in JOINT_RULES:
        lines.append(f"## {rule}")
        shown = 0
        for sentence in picked[rule]:
            if shown >= perRule:
                break
            good = candidatesFor(sentence, rule, joints, config)
            if not good:
                continue
            shown += 1
            lines.append("")
            lines.append(f"원문  {' '.join(sentence.split())[:160]}")
            for candidate in good:
                lines.append(f"  후보  {' '.join(candidate.text.split())[:160]}")
                lines.append(f"        {candidate.why[:130]}")
        lines.append("")
    return "\n".join(lines)


# ---- 고침의 질. 갈래 셋을 같은 문장에 붙여 블라인드로 견준다 ----


def windowDiff(original: str, candidate: str, width: int = 16) -> str:
    """두 문장이 갈리는 자리만 앞뒤 width 글자와 함께. 후보를 짧게 보이려는 것이고 채점에는 안 쓴다."""
    head = 0
    while head < min(len(original), len(candidate)) and original[head] == candidate[head]:
        head += 1
    tail = 0
    while (
        tail < min(len(original), len(candidate)) - head
        and original[len(original) - 1 - tail] == candidate[len(candidate) - 1 - tail]
    ):
        tail += 1
    start = max(0, head - width)
    left = original[start : len(original) - tail + width]
    right = candidate[start : len(candidate) - tail + width]
    mark = "…" if start else ""
    return f"{mark}{left.strip()} -> {mark}{right.strip()}"


def nounCores(sentence: str) -> list[str]:
    """문장의 명사 어절 (조사를 뗀 것). 차례대로, 겹치지 않게."""
    found: list[str] = []
    for word in words(sentence):
        core = stripJosa(word.core)
        if core and isBareNoun(core) and len(core) >= 2 and core not in found:
            found.append(core)
    return found


def termRetention(sentence: str, output: str) -> float:
    cores = nounCores(sentence)
    return sum(core in output for core in cores) / len(cores) if cores else 1.0


def freePrompt(sentence: str, rule: str, why: str) -> str:
    """usageLift 의 reasonOnly 와 같은 프롬프트. 갈래끼리 견주려면 기준선이 같아야 한다."""
    return "\n".join(
        [
            "사업보고서의 한국어 문장 하나를 고친다.",
            "원문의 뜻과 사실과 숫자와 고유명사와 전문 용어를 보존한다.",
            "원문에 없는 정보는 만들지 않는다.",
            "확실하게 고칠 수 없으면 원문을 그대로 출력한다.",
            "설명과 따옴표 없이 고친 문장만 출력한다.",
            f"규칙: {rule}",
            f"이유: {why}",
            f"고칠 문장: {sentence}",
        ]
    )


def pickPrompt(sentence: str, rule: str, why: str, candidates: list[dict]) -> str:
    """닫힌 목록에서 번호 하나. 문장을 짓지 않는다."""
    lines = [
        "사업보고서의 한국어 문장 하나를 고친다. 문장을 새로 쓰지 않고 아래 후보에서 하나를 고른다.",
        "후보는 모두 다른 사업보고서가 실제로 쓴 꼴이고, 모두 이 규칙을 푼다. 뜻이 가장 잘 맞는 것을 고른다.",
        "어느 후보도 원문의 뜻을 지키지 못하면 0 을 낸다.",
        "설명 없이 번호 하나만 출력한다.",
        f"규칙: {rule}",
        f"이유: {why}",
        f"원문: {sentence}",
        f"0. {KEEP}",
    ]
    lines.extend(f"{number}. {item['change']}   ({item['why']})" for number, item in enumerate(candidates, 1))
    return "\n".join(lines)


def prepareTasks(limit: int, perRule: int, kind: str) -> dict:
    index = loadIndex(kind, defaultUsageRoot())
    if index is None:
        raise SystemExit(f"{kind} 색인이 없다")
    config = reportConfig()
    joints = Joints(index)
    pool: dict[str, list[str]] = {rule: [] for rule in JOINT_RULES}
    for _, text in readCorpus(defaultRoot(), limit):
        for finding in lintText(text, config=config):
            if finding.rule in pool and len(finding.quote) <= MAX_SENTENCE:
                pool[finding.rule].append(finding.quote)
    rng = random.Random(SEED)
    tasks: list[dict] = []
    for rule in JOINT_RULES:
        seen: set[str] = set()
        ordered = [one for one in pool[rule] if not (one in seen or seen.add(one))]
        rng.shuffle(ordered)
        taken = 0
        for sentence in ordered:
            if taken >= perRule:
                break
            made = candidatesFor(sentence, rule, joints, config)
            if not made:
                continue
            taken += 1
            why = next(f.why for f in lintText(sentence, config=config) if f.rule == rule)
            shown = [{"change": windowDiff(sentence, one.text), "why": one.why} for one in made]
            tasks.append(
                {
                    "id": f"{rule}-{taken:03d}",
                    "rule": rule,
                    "sentence": sentence,
                    "why": why,
                    "candidates": [{"text": one.text, "why": one.why, "change": windowDiff(sentence, one.text)} for one in made],
                    "prompts": {
                        "free": freePrompt(sentence, rule, why),
                        "pick": pickPrompt(sentence, rule, why, shown),
                    },
                }
            )
    return {
        "version": 1,
        "kind": kind,
        "documents": index.documents,
        "corpusFiles": limit,
        "perRule": perRule,
        "maxSentence": MAX_SENTENCE,
        "seed": SEED,
        "tasks": tasks,
    }


def readJson(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def writeJson(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def digestOf(data) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def writePrompts(manifest: dict, outDir: Path, batch: int) -> str:
    """서브에이전트가 읽을 묶음 파일. 묶음마다 JSON 배열 하나를 쓰게 한다."""
    outDir.mkdir(parents=True, exist_ok=True)
    made = []
    for arm in ("free", "pick"):
        tasks = manifest["tasks"]
        for start in range(0, len(tasks), batch):
            chunk = tasks[start : start + batch]
            name = f"{arm}-{start // batch + 1:02d}"
            body = [
                f"# {name}",
                "",
                f"아래 과제 {len(chunk)}개를 차례대로 푼다. 각 과제의 지시를 그대로 따른다.",
                "",
                '답은 JSON 배열 하나로만 낸다. 항목은 {"taskId": ..., "output": ...} 이고 과제 차례를 지킨다.',
                "`free` 묶음의 output 은 고친 문장 한 줄이고, `pick` 묶음의 output 은 번호 문자열 하나다.",
                "설명, 코드펜스, 다른 키를 넣지 않는다.",
                "",
            ]
            for task in chunk:
                body.append(f"## {task['id']}")
                body.append("")
                body.append(task["prompts"][arm])
                body.append("")
            (outDir / f"{name}.md").write_text("\n".join(body), encoding="utf-8", newline="\n")
            made.append(name)
    return f"{outDir} 에 묶음 {len(made)}개를 썼다: {', '.join(made)}"


def collect(manifest: dict, folder: Path) -> dict:
    """묶음 답 파일들을 하나로 모은다. 파일 이름이 갈래를 정한다 (free-01.json)."""
    known = {task["id"] for task in manifest["tasks"]}
    responses: list[dict] = []
    for path in sorted(folder.glob("*.json")):
        arm = path.stem.split("-")[0]
        if arm not in ("free", "pick"):
            continue
        for item in readJson(path):
            if item["taskId"] not in known:
                raise SystemExit(f"{path.name} 에 모르는 과제 {item['taskId']}")
            responses.append({"taskId": item["taskId"], "arm": arm, "output": str(item["output"]).strip()})
    return {"version": 1, "responses": responses}


def ollamaJson(endpoint: str, route: str, timeout: int, data: dict | None = None) -> dict:
    body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    request = urllib.request.Request(
        endpoint.rstrip("/") + route,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def runOllama(manifest: dict, model: str, endpoint: str, timeout: int) -> dict:
    tags = ollamaJson(endpoint, "/api/tags", timeout)
    found = next((one for one in tags.get("models", []) if one.get("name") == model), None)
    if found is None:
        raise SystemExit(f"Ollama 에 {model} 이 없다")
    responses: list[dict] = []
    total = len(manifest["tasks"]) * 2
    for task in manifest["tasks"]:
        for arm in ("free", "pick"):
            result = ollamaJson(
                endpoint,
                "/api/generate",
                timeout,
                {
                    "model": model,
                    "prompt": task["prompts"][arm],
                    "stream": False,
                    "think": False,
                    "keep_alive": "10m",
                    "options": OLLAMA_OPTIONS,
                },
            )
            output = result.get("response", "").strip().splitlines()
            responses.append({"taskId": task["id"], "arm": arm, "output": output[0].strip() if output else ""})
            if len(responses) % 25 == 0:
                print(f"응답 {len(responses)}/{total}", flush=True)
    model = {key: found[key] for key in ("name", "digest") if key in found}
    return {"version": 1, "runner": {"kind": "ollama", "model": model}, "responses": responses}


def outputText(task: dict, arm: str, responses: dict[tuple[str, str], str]) -> str:
    """갈래의 최종 문장. `top` 은 모델 없이 목록의 첫 후보, `pick` 은 고른 번호의 후보다."""
    if arm == "top":
        return task["candidates"][0]["text"]
    raw = responses.get((task["id"], arm), "")
    if arm == "free":
        return raw or task["sentence"]
    digits = "".join(ch for ch in raw if ch.isdigit())
    number = int(digits) if digits else 0
    if 1 <= number <= len(task["candidates"]):
        return task["candidates"][number - 1]["text"]
    return task["sentence"]


def judgePrompts(manifest: dict, responses: dict, outDir: Path, batch: int) -> str:
    """블라인드 비교 묶음. 과제마다 갈래 차례를 씨앗으로 섞고 이름을 숨긴다."""
    outDir.mkdir(parents=True, exist_ok=True)
    table = {(one["taskId"], one["arm"]): one["output"] for one in responses["responses"]}
    tasks = manifest["tasks"]
    keyPath = []
    made = []
    for start in range(0, len(tasks), batch):
        chunk = tasks[start : start + batch]
        name = f"judge-{start // batch + 1:02d}"
        body = [
            f"# {name}",
            "",
            "사업보고서 문장을 고친 세 가지를 견준다. 각 과제에서 **원문의 뜻을 지키면서 가장 자연스러운 한국어**를",
            "고른다. 셋이 사실상 같으면 `same` 을 낸다. 어느 것도 원문보다 낫지 않으면 `none` 을 낸다.",
            "규칙 이름이나 도구를 짐작해서 고르지 않는다. 읽어서 판단한다.",
            "",
            '답은 JSON 배열 하나로만 낸다. 항목은 {"taskId": ..., "best": ...,',
            '"why": "한 문장"} 이고 best 는 "A", "B", "C", "same", "none" 가운데 하나다.',
            "",
        ]
        for task in chunk:
            rng = random.Random(f"{SEED}-{task['id']}")
            order = list(ARMS)
            rng.shuffle(order)
            keyPath.append({"taskId": task["id"], "order": order})
            body.append(f"## {task['id']}")
            body.append("")
            body.append(f"원문: {task['sentence']}")
            for label, arm in zip("ABC", order, strict=True):
                body.append(f"{label}: {outputText(task, arm, table)}")
            body.append("")
        (outDir / f"{name}.md").write_text("\n".join(body), encoding="utf-8", newline="\n")
        made.append(name)
    writeJson(outDir / "order.json", {"version": 1, "orders": keyPath})
    return f"{outDir} 에 심판 묶음 {len(made)}개와 order.json 을 썼다"


def signTest(wins: int, losses: int) -> float:
    total = wins + losses
    if total == 0:
        return 1.0
    extreme = max(wins, losses)
    tail = sum(math.comb(total, k) for k in range(extreme, total + 1)) / (2**total)
    return min(1.0, 2 * tail)


def scoreTrial(manifest: dict, responses: dict, judgments: Path | None, orders: Path | None) -> str:
    config = reportConfig()
    table = {(one["taskId"], one["arm"]): one["output"] for one in responses["responses"]}
    tasks = manifest["tasks"]
    counts = ", ".join(f"{rule} {sum(one['rule'] == rule for one in tasks)}" for rule in JOINT_RULES)
    lines = [f"과제 {len(tasks)}개 ({counts}), 근거 문서 {manifest['documents']}편", ""]
    lines.append(f"{'갈래':<8}{'규칙 해결':>10}{'새 지적':>10}{'원문 그대로':>12}{'뜻 보존':>10}")
    outputs: dict[str, dict[str, str]] = {}
    for arm in ARMS:
        solved = added = same = 0
        retention = 0.0
        outputs[arm] = {}
        for task in tasks:
            text = outputText(task, arm, table)
            outputs[arm][task["id"]] = text
            before = sentenceTally(task["sentence"], config)
            after = sentenceTally(text, config)
            solved += after.get(task["rule"], 0) < before.get(task["rule"], 0)
            added += any(count > before.get(name, 0) for name, count in after.items())
            same += text.strip() == task["sentence"].strip()
            retention += termRetention(task["sentence"], text)
        lines.append(f"{arm:<8}{solved:>7}/{len(tasks)}{added:>10}{same:>12}{retention / len(tasks):>10.3f}")

    if judgments and judgments.exists():
        verdicts = {}
        for path in sorted(judgments.glob("*.json")) if judgments.is_dir() else [judgments]:
            if path.name == "order.json":
                continue
            for item in readJson(path):
                verdicts[item["taskId"]] = item["best"]
        order = {one["taskId"]: one["order"] for one in readJson(orders)["orders"]} if orders else {}
        tally = dict.fromkeys([*ARMS, "same", "none"], 0)
        for taskId, best in verdicts.items():
            if best in ("same", "none"):
                tally[best] += 1
            elif taskId in order and best in "ABC":
                tally[order[taskId]["ABC".index(best)]] += 1
        lines.append("")
        lines.append(f"블라인드 선호 (심판 {len(verdicts)}건)")
        for key in [*ARMS, "same", "none"]:
            lines.append(f"  {key:<8}{tally[key]:>5}")
        for arm in ("pick", "top"):
            wins, losses = tally[arm], tally["free"]
            lines.append(f"  {arm} 대 free: {wins} 대 {losses}, 부호검정 p {signTest(wins, losses):.4f}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, files, each in (("census", 300, 200), ("show", 60, 6)):
        one = sub.add_parser(name)
        one.add_argument("--limit", type=int, default=files)
        one.add_argument("--per-rule", type=int, default=each)
        one.add_argument("--kind", default="report")
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--limit", type=int, default=300)
    prepare.add_argument("--per-rule", type=int, default=75)
    prepare.add_argument("--kind", default="report")
    prepare.add_argument("--output", type=Path, required=True)

    prompts = sub.add_parser("prompts")
    prompts.add_argument("manifest", type=Path)
    prompts.add_argument("--output-dir", dest="outputDir", type=Path, required=True)
    prompts.add_argument("--batch", type=int, default=25)

    gather = sub.add_parser("collect")
    gather.add_argument("manifest", type=Path)
    gather.add_argument("folder", type=Path)
    gather.add_argument("--output", type=Path, required=True)

    local = sub.add_parser("run")
    local.add_argument("manifest", type=Path)
    local.add_argument("--ollama-model", dest="model", required=True)
    local.add_argument("--endpoint", default="http://127.0.0.1:11434")
    local.add_argument("--timeout", type=int, default=300)
    local.add_argument("--output", type=Path, required=True)

    judge = sub.add_parser("judge")
    judge.add_argument("manifest", type=Path)
    judge.add_argument("responses", type=Path)
    judge.add_argument("--output-dir", dest="outputDir", type=Path, required=True)
    judge.add_argument("--batch", type=int, default=25)

    final = sub.add_parser("score")
    final.add_argument("manifest", type=Path)
    final.add_argument("responses", type=Path)
    final.add_argument("--judgments", type=Path, default=None)
    final.add_argument("--orders", type=Path, default=None)

    args = parser.parse_args()
    if args.command == "census":
        print(census(args.limit, args.per_rule, args.kind))
    elif args.command == "show":
        print(show(args.limit, args.per_rule, args.kind))
    elif args.command == "prepare":
        manifest = prepareTasks(args.limit, args.per_rule, args.kind)
        writeJson(args.output, manifest)
        print(f"과제 {len(manifest['tasks'])}개를 {args.output} 에 썼다. SHA256 {digestOf(manifest)[:24]}…")
    elif args.command == "prompts":
        print(writePrompts(readJson(args.manifest), args.outputDir, args.batch))
    elif args.command == "collect":
        gathered = collect(readJson(args.manifest), args.folder)
        writeJson(args.output, gathered)
        print(f"응답 {len(gathered['responses'])}개를 {args.output} 에 썼다. SHA256 {digestOf(gathered)[:24]}…")
    elif args.command == "run":
        gathered = runOllama(readJson(args.manifest), args.model, args.endpoint, args.timeout)
        writeJson(args.output, gathered)
        print(f"응답 {len(gathered['responses'])}개를 {args.output} 에 썼다. SHA256 {digestOf(gathered)[:24]}…")
    elif args.command == "judge":
        print(judgePrompts(readJson(args.manifest), readJson(args.responses), args.outputDir, args.batch))
    else:
        print(scoreTrial(readJson(args.manifest), readJson(args.responses), args.judgments, args.orders))


if __name__ == "__main__":
    main()
