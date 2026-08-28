"""기준 말뭉치의 실제 종결 활용형을 형태 층이 얼마나 다시 만드는지 잰다.

합니다체와 한다체 입력은 (어간, 종류, 시제, 서법)으로 푼 뒤 같은 문체로 렌더링한 글자가 원문과
같아야 바르게 만든 것으로 센다. 그렇게 확인한 입력만 다른 문체 생성 수에 넣는다. 해요체 입력은
표층만으로 원어간을 되찾지 못하는 자리가 많아 파싱하지 않고, 확인된 다른 문체 입력에서 해요체를
만든 수만 기록한다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from hanlint import Config, fingerprint  # noqa: E402
from hanlint.analysis.grammar import (  # noqa: E402
    DECLARATIVE,
    HAEYO,
    REGISTERS,
    lastWord,
    parsePredicate,
    registerOfWord,
    render,
)

CORPUS_ROOT = (REPO / "../hanlint.out/corpus").resolve()
OUTPUT = REPO / "tests" / "_attempts" / "corpus" / "grammarMetrics.json"
WORD = re.compile(r"[가-힣]+")
TOP = 40


def readJson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def previousWord(text: str, word: str) -> str | None:
    body = text[: text.rfind(word)]
    words = WORD.findall(body)
    return words[-1] if words else None


def topRows(counter: Counter, limit: int = TOP) -> list[list[str | int]]:
    return [[word, count] for word, count in counter.most_common(limit)]


def observe() -> dict:
    metadata = readJson(CORPUS_ROOT / "metadata.json")["documents"]
    source = Counter()
    parsed = Counter()
    reproduced = Counter()
    made = Counter()
    roundTrips = Counter()
    words = Counter()
    unparsed = Counter()
    notReproduced = Counter()
    examples: dict[str, dict[str, str]] = {}
    doublePassives = Counter()
    causatives = Counter()
    sentenceCount = 0

    for entry in metadata:
        text = (CORPUS_ROOT / entry["path"]).read_text(encoding="utf-8")
        doc = fingerprint(text, Config(preset=entry["preset"]), path=entry["path"])
        sentenceCount += len(doc.sentences)
        for sentence in doc.sentences:
            doublePassives.update(sentence.passives)
            causatives.update(match.group(0) for match in re.finditer(r"[가-힣]+게\s+만들[가-힣]*", sentence.text))
            if sentence.mood != "평서":
                continue
            word = lastWord(sentence.text)
            register = registerOfWord(word)
            if register is None:
                continue
            source[register] += 1
            words[(register, word)] += 1
            if register == HAEYO:
                continue
            predicate = parsePredicate(word, previousWord(sentence.text, word))
            if predicate is not None and predicate.mood != DECLARATIVE:
                source[register] -= 1
                words[(register, word)] -= 1
                continue
            if predicate is None:
                unparsed[(register, word)] += 1
                continue
            parsed[register] += 1
            rebuilt = render(predicate, register)
            if rebuilt != word:
                notReproduced[(register, word, rebuilt)] += 1
                continue
            reproduced[register] += 1
            for target in REGISTERS:
                made[target] += 1
                generated = render(predicate, target)
                key = f"{register}:{word}"
                examples.setdefault(key, {"source": word, "sourceRegister": register})[target] = generated
                if target == HAEYO:
                    continue
                reparsed = parsePredicate(generated, previousWord(sentence.text, word))
                if reparsed is not None and render(reparsed, register) == word:
                    roundTrips[f"{register}->{target}->{register}"] += 1

    sourceRows = {}
    for register in REGISTERS:
        total = source[register]
        sourceRows[register] = {
            "total": total,
            "unique": len({word for (foundRegister, word), count in words.items() if foundRegister == register and count > 0}),
            "parsed": parsed[register],
            "reproduced": reproduced[register],
            "reproducedShare": round(reproduced[register] / total, 4) if total else 0.0,
        }
    orderedExamples = sorted(
        examples.items(),
        key=lambda item: (-words[(item[1]["sourceRegister"], item[1]["source"])], item[0]),
    )
    selectedExamples = dict(orderedExamples[:TOP])
    return {
        "version": 1,
        "corpus": {"documents": len(metadata), "sentences": sentenceCount},
        "sourceForms": sourceRows,
        "made": dict(made),
        "roundTrips": dict(sorted(roundTrips.items())),
        "unparsed": topRows(unparsed),
        "notReproduced": [
            [register, word, rebuilt, count] for (register, word, rebuilt), count in notReproduced.most_common(TOP)
        ],
        "frequentForms": selectedExamples,
        "voice": {
            "doublePassiveOccurrences": sum(doublePassives.values()),
            "doublePassiveForms": topRows(doublePassives),
            "causativeOccurrences": sum(causatives.values()),
            "causativeForms": topRows(causatives),
        },
    }


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="기준 말뭉치에서 형태 층의 활용형 재현 범위를 잰다")
    parser.add_argument("--check", action="store_true", help="기록을 다시 재어 글자 단위로 견준다")
    return parser.parse_args()


def main() -> int:
    args = parseArgs()
    measured = observe()
    if args.check:
        if readJson(OUTPUT) != measured:
            print(f"다시 재야 한다: {OUTPUT.relative_to(REPO)}")
            return 1
        print(f"형태 층 측정 기록이 같다: 문장 {measured['corpus']['sentences']}개")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(measured, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"형태 층을 문장 {measured['corpus']['sentences']}개에서 쟀다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
