from __future__ import annotations

import re
from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import SENTENCE, Finding
from ..registry import rule

DOUBLE_NEGATIVE = re.compile(
    r"(하지 않으면 안 (?:된다|됩니다)|하지 않을 수 없(?:다|습니다)|지 않으면 안 (?:된다|됩니다)|지 않을 수 없(?:다|습니다))"
)
FIXES = {
    "하지 않으면 안 된다": "해야 한다",
    "하지 않으면 안 됩니다": "해야 합니다",
    "하지 않을 수 없다": "한다",
    "하지 않을 수 없습니다": "합니다",
}


@rule("doubleNegative")
def doubleNegative(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """하지 않으면 안 된다, 하지 않을 수 없다 같은 이중 부정.

    왜: 부정을 두 번 겹쳐 긍정을 만들면 독자가 한 번 더 뒤집어 읽는다. 일본어 직역에서 온 꼴이다.
    어디서: urimal.org 김민지 2020 번역 투, 나무위키 이중 부정.
    고치기: 긍정으로 쓴다. 노력하지 않으면 안 된다 는 노력해야 한다, 잊지 않을 수 없다 는 잊는다.
        하다 동사는 기계가 fix 로 낸다.
    안 잡는 것: 뜻을 일부러 약하게 하는 이중 부정 (나쁘지 않다). 그것은 다른 구문이다.
    """
    for sentence in doc.sentences:
        match = DOUBLE_NEGATIVE.search(sentence.text)
        if not match:
            continue
        replacement = FIXES.get(match.group(1))
        fix = sentence.text[: match.start()] + replacement + sentence.text[match.end() :] if replacement else None
        yield Finding(
            "doubleNegative",
            sentence.line,
            sentence.text,
            f"`{match.group(1)}` 는 이중 부정이다. 긍정으로 쓴다",
            fix,
            "error",
            SENTENCE,
            sentence.index,
            match.group(1) if replacement else None,
            replacement,
        )
