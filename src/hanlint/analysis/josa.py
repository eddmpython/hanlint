"""받침에 따라 꼴이 갈리는 조사를 맞춘다. 분석기와 무관하게 참인 한국어 사실이라 여기 둔다.

**왜 있는가.** 실측: `이슈로 알려 주면 된다` 에서 `이슈` 를 `쟁점` 으로 바꾸라는 제안이
`쟁점로 알려 주면 된다` 를 냈다. 받침 뒤는 `으로` 다. **한국어 린터가 비문을 고침이라고 내밀고
있었다.** 이 저장소의 README 출력에도 그대로 있었다.

낱말을 바꾸면 뒤에 붙은 조사의 꼴이 따라 바뀐다. 사전이 낱말만 갈아 끼우면 그 문장이 틀린다.
"""

from __future__ import annotations

PAIRS: tuple[tuple[str, str], ...] = (
    ("으로부터", "로부터"),
    ("으로서", "로서"),
    ("으로써", "로써"),
    ("이라고", "라고"),
    ("이라서", "라서"),
    ("이라는", "라는"),
    ("이라면", "라면"),
    ("이나마", "나마"),
    ("으로", "로"),
    ("이란", "란"),
    ("이라", "라"),
    ("이며", "며"),
    ("이랑", "랑"),
    ("이든", "든"),
    ("이나", "나"),
    ("이여", "여"),
    ("이야", "야"),
    ("은", "는"),
    ("이", "가"),
    ("을", "를"),
    ("과", "와"),
    ("아", "야"),
)
"""(받침 뒤 꼴, 받침 없는 뒤 꼴). 긴 것부터 대조해야 `으로` 가 `은` 보다 먼저 걸린다."""

HANGUL_BASE = 0xAC00
HANGUL_LAST = 0xD7A3
JONGSEONG_COUNT = 28
"""한글 음절 하나에 들어가는 종성 자리 수. 0 이 받침 없음이다."""
RIEUL = 8
"""종성 표에서 `ㄹ` 의 자리. `으로` 만 이 받침을 없는 것처럼 다룬다 (`서울로`, `실행로`가 아니라 `실행으로`)."""


def finalOf(word: str) -> int | None:
    """마지막 글자의 종성 번호. 한글이 아니면 None 이라 손대지 않는다."""
    if not word:
        return None
    code = ord(word[-1])
    if not HANGUL_BASE <= code <= HANGUL_LAST:
        return None
    return (code - HANGUL_BASE) % JONGSEONG_COUNT


def josaSwap(word: str, following: str) -> tuple[str, str] | None:
    """`word` 뒤 첫 조사가 바뀌어야 하면 (지금 꼴, 바꿀 꼴). 안 바뀌거나 조사가 아니면 None.

    한글로 끝나지 않는 낱말 (영문, 숫자, 기호) 은 읽는 법이 갈려 손대지 않는다. 고쳐야 할 자리를
    놓치는 쪽이 멀쩡한 문장을 망가뜨리는 쪽보다 낫다.
    """
    final = finalOf(word)
    if final is None or not following:
        return None
    for withFinal, withoutFinal in PAIRS:
        for form in (withFinal, withoutFinal):
            if not following.startswith(form):
                continue
            rest = following[len(form) :]
            if rest and rest[0].isalnum():
                # 조사가 아니라 더 긴 낱말의 앞머리다 (`이유`, `과정`, `로그`). 한글도 isalnum 이 참이다
                break
            if withFinal == "으로":
                wanted = withoutFinal if final in (0, RIEUL) else withFinal
            else:
                wanted = withFinal if final else withoutFinal
            return None if wanted == form else (form, wanted)
    return None


def fitJosa(word: str, following: str) -> str:
    """`word` 뒤에 오는 `following` 의 첫 조사 꼴을 받침에 맞춘 글. 바꿀 것이 없으면 그대로다."""
    swap = josaSwap(word, following)
    if swap is None:
        return following
    form, wanted = swap
    return wanted + following[len(form) :]
