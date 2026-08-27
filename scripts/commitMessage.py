"""커밋 메시지 규칙의 기계 정본.

규칙 문장의 정본은 skills/specs/operation/sourceControl.md 이고 이 파일은 그 문장을 판정 가능한 술어로
옮긴 것이다. .githooks/commit-msg 가 부르고 tests/gates/testCommitMessage.py 가 양성과 음성 fixture 로
이빨을 증명한다. 안 무는 게이트는 없는 게이트보다 나쁘다.

제목 길이는 문자 수 계약이다. sh 와 awk 는 UTF-8 을 바이트로 세서 한국어 제목이 3배로 왜곡되므로
파이썬으로 센다. 표준 라이브러리만 쓴다.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# 한 곳에 모은 상수와 출처. 값은 git 관례와 터미널 가독폭에서 온다.
SUBJECT_MAX = 72
"""git 관례 50 ~ 72. git log --oneline 이 접히지 않는 상한."""
CATEGORY_MAX = 16
"""`릴리즈 v0.0.10:` 까지 담는 분류 폭."""
SUMMARY_MIN = 6
"""`수리` 같은 한 단어 제목이 요약을 대신하는 것을 막는 하한."""
BODY_MIN_LINES = 2
"""무엇을 바꿨는지 + 왜와 검증. 1줄은 제목 반복으로 퇴화한다."""
BODY_MIN_CHARS = 80
"""2줄이 `수리함.` 식으로 비는 것을 막는 하한."""
BODY_LINE_MAX = 100
"""이보다 길면 diff 뷰에서 접힌다."""

# 이스케이프로 적는다. 리터럴로 쓰면 이 파일이 pre-commit 과 대시 게이트에 걸린다.
EM_DASH = "\u2014"
EN_DASH = "\u2013"

# 절대 게이트: 도구와 생성과 기여자 흔적. 이 파일 자신이 문서 게이트에 걸리지 않게 낱말을 `+` 로
# 이어 붙여 만든다 (포매터는 `+` 결합을 합치지 않는다). `ai` 는 단어 경계로만 잡는다. fail, chain 이
# 걸리면 안 된다.
TRACE_WORD_AI = re.compile(r"(^|[^0-9a-z_])ai([^0-9a-z_]|$)", re.IGNORECASE)
TRACE_TERMS = re.compile(
    "|".join(
        [
            "gpt",
            "chat" + "gpt",
            "open" + "ai",
            "co" + "dex",
            "cla" + "ude",
            "anthro" + "pic",
            r"generated\s+by",
            "co-authored" + "-by",
            "assisted" + "-by",
        ]
    ),
    re.IGNORECASE,
)
VERIFICATION_HINT = re.compile(r"(게이트|검증|음성 시험|재현|pytest|green|GREEN|PASS|red|RED)")
HANGUL = re.compile(r"[가-힣]")
GENERATED_SUBJECT = re.compile(r"^(Merge\s|Revert\s|fixup!|squash!|amend!)")
SCISSORS = re.compile(r"^-{2,}\s*>8\s*-{2,}")
SUBJECT_FORM = re.compile(r"^([^:\n]+):\s(\S.*)$")


@dataclass(frozen=True)
class Violation:
    code: str
    message: str


def normalizeMessage(raw: str) -> list[str]:
    """주석 줄과 scissors 아래를 걷어 내고 후행 공백을 지운 줄 목록."""
    lines: list[str] = []
    for line in raw.replace("\r\n", "\n").split("\n"):
        if SCISSORS.match(line):
            break
        if line.startswith("#"):
            continue
        lines.append(line.rstrip())
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def containsTrace(text: str) -> bool:
    """도구, 생성, 기여자 흔적이 있는가. 문서 게이트도 같은 판정을 쓴다."""
    return bool(TRACE_WORD_AI.search(text) or TRACE_TERMS.search(text))


def checkCommitMessage(raw: str) -> list[Violation]:
    """위반을 코드와 함께 돌려준다. 코드로 단정해야 음성 시험이 문구 표류에 흔들리지 않는다."""
    lines = normalizeMessage(raw)
    violations: list[Violation] = []

    def fail(code: str, message: str) -> None:
        violations.append(Violation(code, message))

    text = "\n".join(lines)
    if not text.strip():
        fail("empty", "커밋 메시지가 비어 있다")
        return violations
    if containsTrace(text):
        fail("traceTerm", "도구, 생성, 기여자 흔적 용어가 들어 있다 (절대 게이트)")
    if EM_DASH in text or EN_DASH in text:
        fail("dash", "em 대시나 en 대시가 들어 있다. 마침표로 끊거나 물결표를 쓴다")

    subject, *rest = lines
    if GENERATED_SUBJECT.match(subject):
        return violations

    if len(subject) > SUBJECT_MAX:
        fail("subjectTooLong", f"제목이 {SUBJECT_MAX}자를 넘는다")
    if re.search(r"[.。]$", subject):
        fail("subjectPunctuation", "제목은 마침표로 끝내지 않는다")
    if not HANGUL.search(subject):
        fail("subjectNotKorean", "제목은 한국어다 (분류의 기술 명칭은 원어 유지)")
    form = SUBJECT_FORM.match(subject)
    if not form:
        fail("subjectForm", "제목은 `분류: 요약` 형식이다 (예: `규칙: 이중 피동을 잡는다`)")
    else:
        category, summary = form.group(1), form.group(2)
        if len(category) > CATEGORY_MAX:
            fail("categoryTooLong", f"분류가 {CATEGORY_MAX}자를 넘는다")
        if len(summary) < SUMMARY_MIN:
            fail("summaryTooThin", f"요약이 {SUMMARY_MIN}자보다 짧다")

    if not rest:
        fail("bodyMissing", "본문이 없다. 제목 한 줄은 기록이 아니라 라벨이다")
        return violations
    if rest[0] != "":
        fail("blankLineMissing", "제목과 본문 사이에 빈 줄이 필요하다")

    body = rest[1:]
    contentLines = [line for line in body if line]
    if len(contentLines) < BODY_MIN_LINES:
        fail("bodyTooShort", f"본문은 최소 {BODY_MIN_LINES}줄이다 (무엇을 바꿨는지 + 왜와 검증)")
    if len("".join(contentLines)) < BODY_MIN_CHARS:
        fail("bodyTooThin", f"본문이 {BODY_MIN_CHARS}자보다 얇다")
    if any(len(line) > BODY_LINE_MAX for line in body):
        fail("bodyLineTooLong", f"본문 줄이 {BODY_LINE_MAX}자를 넘는다")
    if not HANGUL.search("\n".join(contentLines)):
        fail("bodyNotKorean", "본문은 한국어다")
    if not any(VERIFICATION_HINT.search(line) for line in contentLines):
        fail(
            "verificationMissing",
            "본문에 검증 사실이 없다 (어느 게이트가 green 인지, 신설 게이트면 음성 시험 결과)",
        )
    return violations


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("blocked: 커밋 메시지 파일 인자가 없다", file=sys.stderr)
        return 1
    violations = checkCommitMessage(Path(argv[1]).read_text(encoding="utf-8"))
    if not violations:
        return 0
    print("blocked: 커밋 메시지가 규칙 (operation.sourceControl) 을 어긴다", file=sys.stderr)
    for violation in violations:
        print(f"  - [{violation.code}] {violation.message}", file=sys.stderr)
    print("", file=sys.stderr)
    print("형식:", file=sys.stderr)
    print("  분류: 무엇을 했는지 한 줄 요약", file=sys.stderr)
    print("", file=sys.stderr)
    print("  무엇을 어떻게 바꿨는지 (파일과 심볼 수준).", file=sys.stderr)
    print("  왜 필요했는지 (문제와 근거).", file=sys.stderr)
    print("  검증: 어느 게이트가 green 인지. 신설 게이트면 음성 시험 결과.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
