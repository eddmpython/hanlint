---
id: operation.codeStyle
title: 코드 스타일
category: operation
purpose: 이름, 크기, 타입, docstring, 예외, 상수, 테스트, 도구. 강행규칙 (CLAUDE.md) 이 한 줄로 말한 것을 판단 가능한 세부로 푼다.
whenToUse:
  - 이 이름이 규칙에 맞나
  - 상수는 어떻게 적나
  - 규칙 docstring 은 무엇을 담나
  - 테스트 파일 이름
  - 린터 설정
verify:
  - .venv/Scripts/python.exe -X utf8 -B -m pytest tests/gates/testNaming.py -q
status: curated
---

# 코드 스타일

강행규칙은 루트 `CLAUDE.md` 다. 여기는 그 규칙의 세부이고, 기계가 잡는 것은 `tests/gates/testNaming.py` 와
`hooks/writeGate.py` 가 집행한다.

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

snake_case 는 승인된 적 없다. 예외는 외부 명칭뿐이다. Kiwi 태그 (`NNG`), 서드파티 함수의 키워드 인자
(`ensure_ascii=False`), 프로토콜 키. 호출 측 키워드는 외부 계약이라 게이트가 보지 않고, 정의 측 (함수 정의,
인자, 대입) 만 본다. `__init__.py` 와 `conftest.py` 는 파이썬이 정한 이름이라 예외다.

이름은 짧고 직관적으로. `parseMarkdown` 이지 `parseMarkdownTextIntoDocumentModel` 이 아니다. 문장을 이름으로
쓰지 않는다. 동사로 시작하는 함수, 명사인 변수.

## 크기와 모양

- 함수 하나는 한 화면 안에, 한 일만 한다. 두 일을 하면 이름에 `And` 가 들어가고 그때 나눈다.
- 조기 return. 중첩을 세 단계 넘기지 않는다.
- `dataclass(frozen=True)` 를 값 객체의 기본으로. 가변이 필요할 때만 푼다.
- 공개 함수는 타입 힌트를 전부 붙인다. 내부 함수도 인자에는 붙인다.
- `from __future__ import annotations` 를 모든 모듈 첫 줄에.
- import 순서: 표준 라이브러리, 빈 줄, 패키지 내부 (아래층만). 서드파티는 kiwi 어댑터 안에서만 지연 import.

## docstring

모듈과 공개 함수는 docstring 을 갖는다. 첫 줄은 마침표로 끝나는 한 문장이다.

**규칙 함수의 docstring 은 기술서다.** `hanlint explain <규칙>` 이 그대로 출력한다. 네 절을 이 순서로 쓴다.

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

`왜`, `어디서`, `고치기`, `안 잡는 것` 네 줄이 없는 규칙은 등록부가 거부한다 (M1 에서 게이트로).

## 상수와 값

- 임계는 `config/settings.py` 의 `Config` 필드가 정본이다. 규칙 함수 안에 숫자를 박지 않는다.
- 사전과 표지 목록은 `data/` 다. 코드 안에 낱말 목록을 두지 않는다.
- 불가피한 상수는 모듈 위에 UPPER_SNAKE 로 한 곳에 두고 출처를 주석으로 남긴다.

## 예외

- `except Exception: pass` 처럼 삼키지 않는다. 좁은 예외를 잡고 컨텍스트를 담아 다시 던지거나 사용자에게
  다음 행동을 말한다.
- 사용자에게 보이는 오류는 무엇이 잘못됐는지 + 다음에 할 일. `글.md 를 찾지 못했다. 경로를 확인하거나
  hanlint --help`.

## 주석

왜 그렇게 했는지만 적는다. 무엇을 하는지는 코드가 말한다. 되돌린 시도는 이유와 함께 남긴다. em 대시를
쓰지 않는다. 도구와 생성 주체 표식을 넣지 않는다.

## 테스트

- 규칙 하나에 fixture 하나 (`tests/fixtures/rules/<규칙>.json`, `catch` 와 `spare`). 테스트는 fixture 를 읽어
  두 분석기 모두에 돌린다.
- 게이트는 순수 함수 + 양성·음성 fixture 로 이빨을 증명한다. 통과만 확인한 게이트는 게이트가 아니다.
- 테스트 이름은 무엇을 확인하는지 읽히게. `testSparesSimplePassive`.

## 도구

- 런타임 의존성 0. dev 도구는 `[project.optional-dependencies].dev` 에만 둔다. pytest, ruff.
- ruff: 포맷과 E, F, W, I, B, UP. **N (pep8-naming) 은 선택하지 않는다.** camelCase 와 충돌한다. 이름은
  우리 게이트가 본다.
- pytest 는 `python_files = ["test*.py"]` 로 camelCase 테스트 파일을 수집한다. 설정은 `pyproject.toml`.
- `python` 은 항상 `-X utf8 -B`. `-B` 가 `__pycache__` 를 막고, pytest 와 ruff 의 캐시는 `pyproject.toml` 이
  저장소 밖 `../hanlint.out/` 으로 보낸다. 저장소 안에 임시 산출물을 두지 않는다.

## 되돌리기

이름 규칙을 어긴 파일은 `git mv` 로 이름을 바꾸고 참조처를 고친다. 게이트가 다시 본다.
