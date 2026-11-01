---
id: operation.codeStyle
title: 코드 스타일
category: operation
purpose: 이름, 크기, 타입, docstring, 예외, 상수, 테스트, 도구의 기준. 꼭 지킬 규칙(CLAUDE.md)이 한 줄로 말한 것을 판단할 수 있는 세부로 푼다.
whenToUse:
  - 이 이름이 규칙에 맞나
  - 상수는 어떻게 적나
  - 규칙 docstring은 무엇을 담나
  - 테스트 파일 이름
  - 린터 설정
verify:
  - .venv/Scripts/python.exe -X utf8 -B -m pytest tests/gates/testNaming.py -q
status: curated
---

# 코드 스타일

꼭 지킬 규칙은 루트 `CLAUDE.md`에 있다. 이 문서는 그 규칙의 세부이고, 기계가 잡는 것은 `tests/gates/testNaming.py`와
`hooks/writeGate.py`가 막는다.

## 이름

| 무엇 | 꼴 | 예 |
|---|---|---|
| 파일, 폴더 | camelCase | `parseMarkdown.py`, `rules/sentence/doublePassive.py` |
| 함수, 메서드, 변수, 인자 | camelCase | `lintText`, `startLine`, `nounPileMin` |
| 클래스 | PascalCase | `Finding`, `SentencePrint` |
| 모듈 상수 | UPPER_SNAKE | `NOUN_TAGS`, `SUBJECT_MAX` |
| 비공개 | `_` 접두 뒤 camelCase | `_sharedAnalyzer`, `_raiseDeadline` |
| dunder | 파이썬 관례 | `__init__`, `__all__` |
| 규칙 id | camelCase. 파일 이름 = 함수 이름 = id | `doublePassive` |
| 테스트 파일 | `test` 접두 camelCase | `tests/rules/testDoublePassive.py` |
| 테스트 함수 | `test` 접두 camelCase | `def testCatchesDoublePassive()` |

snake_case는 승인된 적이 없다. 예외는 외부 명칭뿐이다. 서드파티 함수의 키워드 인자
(`ensure_ascii=False`)와 프로토콜 키가 그렇다. 호출 측 키워드는 외부 계약이라 게이트가 보지 않고, 정의 측(함수 정의,
인자, 대입)만 본다. `__init__.py`와 `conftest.py`는 파이썬이 정한 이름이라 예외다.

이름은 짧고 직관적으로 짓는다. `parseMarkdownTextIntoDocumentModel`이 아니라 `parseMarkdown`으로 쓴다. 문장을 이름으로
쓰지 않는다. 함수 이름은 동사로 시작하고 변수 이름은 명사로 짓는다.

## 크기와 모양

- 함수 하나는 한 화면 안에, 한 일만 한다. 두 일을 하면 이름에 `And`가 들어가고 그때 나눈다.
- 조건이 맞지 않으면 일찍 return한다. 중첩을 세 단계 넘기지 않는다.
- 값 객체는 `dataclass(frozen=True)`를 기본으로 쓴다. 값을 바꿔야 할 때만 푼다.
- 공개 함수는 타입 힌트를 전부 붙인다. 내부 함수도 인자에는 붙인다.
- `from __future__ import annotations`를 모든 모듈 첫 줄에 둔다.
- import 순서는 표준 라이브러리, 빈 줄, 패키지 내부(아래 계층만)다. 런타임 서드파티 의존성은 없다.

## docstring

모듈과 공개 함수는 docstring을 갖는다. 첫 줄은 마침표로 끝나는 한 문장이다.

**규칙 함수의 docstring은 설명서다.** `hanlint explain <규칙>`이 그대로 출력한다. 네 절을 이 순서로 쓴다.

```python
@rule("doublePassive")
def doublePassive(prints, config):
    """되어지다, 보여지다처럼 피동에 -어지다 를 또 붙인 이중 피동.

    왜: 피동이 두 번 겹치면 누가 하는지 한 번 더 흐려진다. 독자는 주어를 찾아 되돌아간다.
    어디서: 국립국어원 어문 규범. im-not-ai A-8 (오경순 2010, 김은일 2015). 우리 글 실측 (날짜, 글).
    고치기: 하나만 남긴다. 되어진다 는 된다, 보여진다 는 보인다.
    안 잡는 것: 만들어진다 같은 단순 피동. 어간이 피동사가 아니면 지적하지 않는다.
    """
```

`왜`, `어디서`, `고치기`, `안 잡는 것` 네 줄이 없는 규칙은 규칙 목록이 거부한다.

## 상수와 값

- 기준값은 `config/settings.py`의 `Config` 필드가 정한다. 규칙 함수 안에 숫자를 박지 않는다.
- 사전과 접속사 목록은 `data/`에 둔다. 코드 안에 단어 목록을 두지 않는다.
- 불가피한 상수는 모듈 위에 UPPER_SNAKE로 한 곳에 두고 출처를 주석으로 남긴다.

## 예외

- `except Exception: pass`처럼 삼키지 않는다. 좁은 예외를 잡고 컨텍스트를 담아 다시 던지거나 사용자에게
  다음 행동을 말한다.
- 사용자에게 보이는 오류는 무엇이 잘못됐는지와 다음에 할 일을 함께 말한다. `글.md를 찾지 못했다. 경로를 확인하거나
  hanlint --help`.

## 주석

왜 그렇게 했는지만 적는다. 무엇을 하는지는 코드가 말한다. 되돌린 시도는 이유와 함께 남긴다. 긴 줄표(U+2014)와 짧은 줄표(U+2013)를
쓰지 않는다. 도구와 생성 주체 표식을 넣지 않는다.

## 테스트

- 규칙 하나에 fixture 하나(`tests/fixtures/rules/<규칙>.json`, `catch`와 `spare`). 테스트는 fixture를 읽어
  Python과 npm 두 구현 모두에서 돌린다.
- 게이트는 순수 함수와 양성·음성 fixture로 실제로 막는지 증명한다. 통과만 확인한 게이트는 무엇을 막는지 알 수 없다.
- 테스트 이름은 무엇을 확인하는지 읽히게 짓는다. 예: `testSparesSimplePassive`.

## 도구

- 런타임 의존성은 없다. Python 개발 도구는 `[dependency-groups]`의 `dev`에 둔다. pytest와 ruff다. `uv sync`가 설치하고 `uv.lock`이
  정확한 버전을 고정한다. pip로 따로 설치하지 않는다.
- 브라우저 화면 검수 도구는 `npm/package.json`의 `devDependencies`가 정확한 버전을 정하고
  `npm/package-lock.json`이 실제 설치본을 고정한다. 제품의 npm `dependencies`에는 넣지 않는다.
- ruff는 포맷과 E, F, W, I, B, UP을 쓴다. **N(pep8-naming)은 선택하지 않는다.** camelCase와 충돌하기 때문이다. 이름은
  우리 게이트가 본다.
- pytest는 `python_files = ["test*.py"]`로 camelCase 테스트 파일을 수집한다. 설정은 `pyproject.toml`.
- `python`은 항상 `-X utf8 -B`로 돌린다. `-B`가 `__pycache__`를 막고, pytest와 ruff의 캐시는 `pyproject.toml`이
  `~/.cache/hanlint/`로 보낸다. 저장소 안에도 저장소 옆에도 임시 산출물을 두지 않는다.

## JavaScript (npm)

`web/`의 브라우저 편집기도 아래 이름과 ESM, JSDoc 규칙을 따른다. 브라우저용 규칙을 따로 만들지 않고
`npm/src/index.js`를 호출한다. 코드 경로 게이트는 `.js`와 `.mjs`, 대시 게이트는 CSS와 SVG도 검사한다.

`npm/`은 파이썬을 옮긴 구현이고 같은 이름 규칙을 따른다. 파일과 폴더와 함수와 변수는 camelCase, 테스트 파일은
`<이름>.test.js`(node의 관례)다. 순수 ESM이고 빌드가 없다. 타입은 JSDoc과 파일 첫 줄의 `// @ts-check`로
편집기가 본다. 런타임 의존성은 없다. 브라우저 화면 검수용 개발 도구만 `npm/node_modules`에 생기며 배포물에는
들어가지 않는다. 파이썬 `re`와 JS `RegExp`, 파이썬 `str`과 JS `String`의 뜻 차이는 `npm/src/regex.js`와
`npm/src/text.js`가 흡수하고 규칙 파일은 그 위에서 파이썬과 같은 문장으로 쓴다. 사전과 규칙 설명서는 손으로
옮기지 않고 `scripts/derive/npmData.py`가 `npm/data`로 옮긴다.

## 되돌리기

이름 규칙을 어긴 파일은 `git mv`로 이름을 바꾸고 참조처를 고친다. 게이트가 다시 본다.
