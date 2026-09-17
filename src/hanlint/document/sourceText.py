"""소스 파일의 글 마디. 사람이 읽는 한국어 문자열 리터럴과 JSX 글을 줄 번호와 함께 뽑는다.

마크다운은 문장이 곧 글이지만 화면의 글은 코드 안에 흩어져 있다. 여기가 그 글을 코드에서 떼어 내는
자리다. 표층만 본다. 언어의 문법을 알지 않고, 따옴표 안의 한국어와 태그 사이의 한국어만 글로 본다.

무엇을 글로 보나
  - 작은따옴표, 큰따옴표, 백틱 안의 한 줄짜리 문자열. 한국어가 하나라도 있는 것만.
  - JSX 의 태그 사이 글 (`>글<`). 식 (`{...}`) 이 끼어도 글로 본다. 식 안의 따옴표 글은 따로 본다.
  - 글 (`text`) 은 파일에 있는 그대로 두어 되돌려 쓸 수 있게 하고, 검사는 식 (`${...}`, `{...}`) 을 비운 `plain` 으로 한다.
  - 러스트의 줄 이음 (역슬래시 + 줄바꿈) 은 한 줄로 이어 한 마디로 본다.

무엇을 빼나
  - 주석 (`//`, `#`, `/* */`, `*` 로 시작하는 줄). 사용자가 읽지 않는다.
  - 개발자용 줄 (`new Error(`, `console.`, `panic!(`, `expect(`, `assert`). 파이썬의 docstring 은 표층으로 못 가르므로
    첫 줄이 글로 잡힌다.
  - 러스트의 시험 모듈 (`#[cfg(test)]` 부터 끝까지).

실측: Taxly 의 화면 소스 92 파일에서 이 규칙으로 글 마디 1,100여 개를 뽑았고, 식이 낀 JSX 글과 러스트 줄 이음을
못 읽어 문장 셋이 샜던 것을 검증에서 잡아 더했다 (2026-09-17).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SOURCE_SUFFIXES = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".rs", ".py")
"""`hanlint sheet` 가 폴더에서 찾는 확장자. 마크다운은 `hanlint 글.md` 의 몫이다."""

KOREAN = re.compile(r"[가-힣]")
QUOTES = ("'", '"', "`")
"""문자열의 경계. 줄을 앞에서부터 훑어 여는 따옴표에서 같은 닫는 따옴표까지를 한 마디로 본다. 정규식으로 따옴표 쌍을
찾으면 한국어 없는 문자열의 닫는 따옴표에서 다음 여는 따옴표까지의 코드를 글로 오독한다 (실측 2026-09-17)."""
BLOCK_COMMENT = re.compile(r"/\*[\s\S]*?\*/")
DEVELOPER_LINE = re.compile(r"new Error\(|console\.|panic!\(|expect\(|assert")
RUST_CONTINUATION = re.compile(r"\\\r?\n[ \t]*")
RUST_TEST_MARKER = "#[cfg(test)]"


@dataclass(frozen=True)
class SourceLiteral:
    line: int
    """1부터 세는 줄 번호. 여러 줄을 이은 러스트 문자열은 시작 줄이다."""
    text: str
    """따옴표와 태그를 뺀 글. 파일에 있는 그대로라 되돌려 쓸 때 찾을 수 있다."""
    plain: str
    """검사에 쓰는 글. 식 (`${...}`, `{...}`) 을 비우고 공백을 하나로 모았다."""
    column: int = 0
    """1부터 세는 칸. 그 줄에서 `text` 가 시작하는 자리라 같은 글이 두 번 있어도 되돌려 쓸 자리가 하나로 정해진다."""


def balancedEnd(line: str, start: int) -> int:
    """`start` 의 `{` 를 닫는 `}` 의 자리. 안의 따옴표 문자열 (중첩 백틱까지) 과 중첩 괄호를 건너뛴다. 없으면 -1."""
    depth = 0
    index = start
    while index < len(line):
        char = line[index]
        if char in QUOTES:
            end = closingQuote(line, index)
            if end < 0:
                return -1
            index = end + 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def expressionSpans(text: str) -> list[tuple[int, int]]:
    """글에 낀 식 `{...}` 와 `${...}` 의 (시작, 끝 다음) 자리. 식 안의 따옴표와 중첩 괄호는 식의 일부다.

    닫히지 않은 식 (여러 줄에 걸친 식의 첫 줄) 은 식으로 보지 않고 그 뒤를 그대로 둔다.
    """
    spans: list[tuple[int, int]] = []
    index = 0
    while index < len(text):
        if text[index] == "{":
            end = balancedEnd(text, index)
            if end < 0:
                break
            start = index - 1 if index > 0 and text[index - 1] == "$" else index
            spans.append((start, end + 1))
            index = end + 1
            continue
        index += 1
    return spans


def withoutTemplateExpressions(source: str) -> str:
    """템플릿 리터럴의 `${ ... }` 식을 (안의 따옴표와 중첩 괄호를 세어) 같은 길이의 빈칸으로 바꾼다. 식은 코드이지 글이 아니다."""
    output = list(source)
    for start, end in expressionSpans(source):
        if source[start] == "$":
            output[start:end] = " " * (end - start)
    return "".join(output)


def userFacingSource(source: str, path: str) -> str:
    """주석과 개발자용 줄을 걷어낸 소스. 줄 번호는 유지한다 (빈 줄로 바꾼다)."""
    isRust = path.endswith(".rs")
    body = source
    if isRust and RUST_TEST_MARKER in body:
        body = body[: body.index(RUST_TEST_MARKER)]
    if isRust:
        body = RUST_CONTINUATION.sub("", body)
    body = BLOCK_COMMENT.sub(lambda match: re.sub(r"[^\n]", " ", match.group(0)), body)
    lines: list[str] = []
    for line in body.split("\n"):
        trimmed = line.strip()
        if trimmed.startswith("//") or trimmed.startswith("*") or trimmed.startswith("#"):
            lines.append("")
        elif DEVELOPER_LINE.search(line):
            lines.append("")
        else:
            lines.append(re.sub(r"//.*$", "", line))
    return "\n".join(lines)


def plainText(text: str) -> str:
    """검사에 쓰는 글. 식 (`${...}`, `{...}`) 을 비우고 공백을 하나로 모은다."""
    pieces: list[str] = []
    cursor = 0
    for start, end in expressionSpans(text):
        pieces.append(text[cursor:start])
        pieces.append(" ")
        cursor = end
    pieces.append(text[cursor:])
    return re.sub(r"\s+", " ", "".join(pieces)).strip()


def closingQuote(line: str, start: int) -> int:
    """`start` 의 따옴표를 닫는 자리. 역슬래시 뒤 글자는 건너뛰고, 백틱 안의 `${...}` 은 안의 백틱까지 통째로 건너뛴다.

    없으면 -1. 실측: `${a ? `해마다 ${b}` : c}은 결산` 의 안쪽 백틱을 바깥의 끝으로 읽어 코드가 글로 샜다 (2026-09-18).
    """
    quote = line[start]
    index = start + 1
    while index < len(line):
        char = line[index]
        if char == "\\":
            index += 2
            continue
        if quote == "`" and char == "$" and index + 1 < len(line) and line[index + 1] == "{":
            end = balancedEnd(line, index + 1)
            if end < 0:
                return -1
            index = end + 1
            continue
        if char == quote:
            return index
        index += 1
    return -1


def tagCloses(line: str, index: int) -> bool:
    """`index` 의 `>` 가 JSX 여는 태그의 끝인가. 태그 이름, 속성 값의 따옴표, 식의 `}` 뒤에 오고 `=` 가 뒤따르지 않는다.

    비교 (`page >= count`, `a > b`), 화살표 (`=>`), 러스트 반환 (`->`) 의 `>` 는 앞이 빈칸이거나 `=`, `-` 이고
    뒤에 `=` 가 올 수 있다. 실측: `disabled={page >= pageCount}` 의 `>` 를 태그 끝으로 읽어 그 뒤 코드가 글로
    잡혔다 (2026-09-17).
    """
    if index == 0 or index + 1 < len(line) and line[index + 1] == "=":
        return False
    before = line[index - 1]
    return before in "\"'}" or before.isalnum()


def jsxTextEnd(line: str, start: int) -> int:
    """`start` 부터의 JSX 글이 끝나는 `<` 의 자리. 식 (`{...}`) 안의 `<` 는 글의 끝이 아니다. 없으면 -1."""
    index = start
    while index < len(line):
        char = line[index]
        if char == "<":
            return index
        if char == "{":
            end = balancedEnd(line, index)
            if end < 0:
                return -1
            index = end + 1
            continue
        index += 1
    return -1


def innerLiterals(text: str, offset: int) -> list[tuple[int, str]]:
    """글에 낀 식 (`{...}`, `${...}`) 안의 글 마디. 식 안은 코드라 따옴표 글과 태그 사이 글을 다시 훑는다."""
    found: list[tuple[int, str]] = []
    for start, end in expressionSpans(text):
        brace = start + 1 if text[start] == "$" else start
        found.extend(lineLiterals(text[brace + 1 : end - 1], offset + brace + 1))
    return found


def lineLiterals(line: str, offset: int = 0) -> list[tuple[int, str]]:
    """한 줄의 글 마디를 (시작 자리, 글) 로 나온 차례로. 따옴표 문자열과 JSX 의 태그 사이 글 (`>글<`) 이다.

    JSX 글의 `>` 는 화살표 (`=>`) 나 러스트 반환 (`->`) 의 `>` 가 아니다. 글에 식 (`{...}`, `${...}`) 이 끼면 그 글을 낸 뒤
    식 안을 따로 훑어 안의 따옴표 글과 태그 사이 글도 낸다 (중첩 식과 중첩 백틱 포함). 식이 없는 글 안은 다시 훑지 않는다
    (글 속 인용 부호를 문자열로 오독하지 않게). 실측: `{cond ? <span>없음</span> : x}` 의 안쪽 `<` 를 글의 끝으로 읽고
    `{[['기준월 실적', a]]}` 의 식을 못 비워 코드가 글로 샜다 (2026-09-18).
    """
    found: list[tuple[int, str]] = []
    index = 0
    while index < len(line):
        char = line[index]
        if char in QUOTES:
            end = closingQuote(line, index)
            if end < 0:
                break
            raw = line[index + 1 : end]
            found.append((offset + index + 1, raw))
            if char == "`":
                found.extend(innerLiterals(raw, offset + index + 1))
            index = end + 1
            continue
        if char == ">" and tagCloses(line, index):
            end = jsxTextEnd(line, index + 1)
            if end > index:
                raw = line[index + 1 : end]
                found.append((offset + index + 1, raw))
                found.extend(innerLiterals(raw, offset + index + 1))
                index = end
                continue
        index += 1
    found.sort(key=lambda item: item[0])
    return found


def sourceLiterals(source: str, path: str = "") -> list[SourceLiteral]:
    """소스에서 글 마디를 줄 번호 순으로. 같은 줄의 마디는 나온 차례다. 한국어가 식 안에만 있는 마디는 뺀다."""
    found: list[SourceLiteral] = []
    for number, line in enumerate(userFacingSource(source, path).split("\n"), 1):
        for start, raw in lineLiterals(line):
            text = raw.strip()
            plain = plainText(text)
            if text and KOREAN.search(plain):
                found.append(SourceLiteral(number, text, plain, start + (len(raw) - len(raw.lstrip())) + 1))
    return found


def replaceLiteral(lineText: str, old: str, new: str) -> tuple[str, int]:
    """한 줄 안에서 글 `old` 를 `new` 로 바꾼다. 몇 번 나왔는지 같이 준다 (한 번일 때만 바꾼 것이 확정이다).

    표에서 고친 글을 파일로 되돌리는 자리다. 글이 그 줄에 정확히 한 번 있어야 바꾼다. 없거나 둘이면 사람이 본다.
    """
    count = lineText.count(old)
    if count != 1:
        return lineText, count
    return lineText.replace(old, new, 1), 1


__all__ = [
    "SOURCE_SUFFIXES",
    "SourceLiteral",
    "plainText",
    "replaceLiteral",
    "sourceLiterals",
    "userFacingSource",
    "withoutTemplateExpressions",
]
