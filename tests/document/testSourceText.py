"""소스의 글 마디 뽑기. 따옴표 글, JSX 글, 식이 낀 JSX 글, 템플릿, 주석과 개발자 줄, 러스트 줄 이음과 시험 모듈."""

from __future__ import annotations

from hanlint.document import replaceLiteral, sourceLiterals

JSX = (
    "// 주석의 한국어는 글이 아니다\n"
    "const LABELS = { pending: '승인 대기', failed: \"요청 실패\" }\n"
    "console.log('개발자만 보는 줄')\n"
    "throw new Error('내부 오류')\n"
    "<p>접수 실패 · 코드: {failure}</p>\n"
    "<span>{count}개 회사</span>\n"
    "<div>{list.map((x) => <Row label='한글' />)}</div>\n"
    "<b onClick={() => go('가')}>확인</b>\n"
    "const t = `최대 ${count}개 · 추가 불가`\n"
    "/* 블록 주석의 한국어 */ const u = 'ok'\n"
)


def texts(source: str, path: str = "a.jsx") -> list[tuple[int, str]]:
    return [(literal.line, literal.text) for literal in sourceLiterals(source, path)]


def testQuotedAndJsxTextWithExpressions():
    assert texts(JSX) == [
        (2, "승인 대기"),
        (2, "요청 실패"),
        (5, "접수 실패 · 코드: {failure}"),
        (6, "{count}개 회사"),
        (7, "한글"),
        (8, "가"),
        (8, "확인"),
        (9, "최대 ${count}개 · 추가 불가"),
    ]


def testPlainTextBlanksExpressions():
    assert [literal.plain for literal in sourceLiterals(JSX, "a.jsx")][2:6] == ["접수 실패 · 코드:", "개 회사", "한글", "가"]
    assert sourceLiterals("const t = `${label ? '한글' : ''}`\n", "a.js") == []


def testRustContinuationAndTestModuleTail():
    source = (
        'fn f() -> Option<&str> { Some("설치 실패\\n\\n\\\n             node build") }\n'
        "#[cfg(test)]\n"
        'mod tests { fn t() { let s = "시험 문자열"; } }\n'
    )
    assert texts(source, "a.rs") == [(1, "설치 실패\\n\\nnode build")]


def testArrowAndTemplateArtifactsAreNotText():
    source = "const rows = list.map((step) => ({ scopeAddress: step.asset, visibleNameKo: `${step.label} 복구 단계 실행` }))\n"
    assert texts(source, "a.js") == [(1, "${step.label} 복구 단계 실행")]
    source = "const a = `x`; const b = { label: `${n}개`, note: '한글' }; f(<i aria-label={ok ? '가' : '나'}>확인</i>)\n"
    assert texts(source, "a.jsx") == [(1, "${n}개"), (1, "한글"), (1, "가"), (1, "나"), (1, "확인")]
    source = "<section role=\"status\" aria-label={busy ? '자료 갱신 중' : '자료 불러오는 중'} aria-live=\"polite\">\n"
    assert texts(source, "a.jsx") == [(1, "자료 갱신 중"), (1, "자료 불러오는 중")]
    assert texts("const s = 'it\\'s 한글'\n", "a.js") == [(1, "it\\'s 한글")]
    source = "<button disabled={page >= pageCount} onClick={() => go(page + 1)}>다음</button> {a > b ? '큼' : '작음'}\n"
    assert texts(source, "a.jsx") == [(1, "다음"), (1, "큼"), (1, "작음")]


def testPythonCommentIsNotText():
    assert texts("# 주석\nLABELS = {'empty': '요청 없음'}\n", "a.py") == [(2, "요청 없음")]


def testReplaceLiteralOnlyWhenUnique():
    assert replaceLiteral("a = '요청 실패'", "요청 실패", "요청 없음") == ("a = '요청 없음'", 1)
    assert replaceLiteral("a = '요청'; b = '요청'", "요청", "x") == ("a = '요청'; b = '요청'", 2)
    assert replaceLiteral("a = 'x'", "없음", "y") == ("a = 'x'", 0)
