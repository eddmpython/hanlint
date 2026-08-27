---
id: operation.verify
title: 검증
category: operation
purpose: 커밋 전에 무엇을 돌리고 무엇이 green 이어야 하는지. 게이트 목록과 각 게이트의 음성 시험.
whenToUse:
  - 커밋 전에 뭘 돌리나
  - 게이트가 뭐가 있나
  - 테스트가 빨간데
  - 자기 검사가 왜 실패하나
verify:
  - .venv/Scripts/python.exe -X utf8 -B -m pytest -q
  - .venv/Scripts/python.exe -X utf8 -B -m ruff check src tests hooks scripts
  - .venv/Scripts/python.exe -X utf8 -B -m ruff format --check src tests hooks scripts
  - python -X utf8 -B hooks/tests/checkWriteGate.py
  - node --test npm/test/*.test.js
status: observed
---

# 검증

커밋 전에 넷이 green 이어야 한다. `pre-push` 가 pytest 를 다시 돈다. pytest 안에 npm 동등성 게이트가 있어
node 가 있는 기계에서는 두 구현의 출력을 글자 단위로 견준다.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest -q
.venv/Scripts/python.exe -X utf8 -B -m ruff check src tests hooks scripts
.venv/Scripts/python.exe -X utf8 -B -m ruff format --check src tests hooks scripts
node --test npm/test/*.test.js
```

`src/hanlint/data` 나 규칙 docstring 을 고쳤으면 `python scripts/exportData.py` 로 `npm/data` 를 다시 만든다.
안 하면 `testNpmData` 가 빨갛다.

## 게이트

| 게이트 | 무엇을 막나 | 음성 시험 |
|---|---|---|
| `tests/rules/testRules.py` | 규칙이 fixture 의 catch 를 놓치거나 spare 를 잡는 것. 두 분석기 모두 | fixture 에 틀린 문장을 넣으면 red |
| `tests/rules/testRegistry.py` | 네 절 없는 규칙 docstring, 이름 어긋난 규칙 | 테스트 안에서 그런 규칙을 등록해 거부를 확인한다 |
| `tests/gates/testNaming.py` | snake_case 파일, 폴더, 함수, 변수 | fixture 로 양방향 |
| `tests/gates/testLayers.py` | 위층 import, 형제 층 교차, 규칙끼리 import | fixture 로 양방향 |
| `tests/gates/testDash.py` | 추적 파일의 em 대시, en 대시 | fixture 로 양방향 |
| `tests/gates/testCommitMessage.py` | 커밋 메시지 형식, 검증 줄 부재, 도구 흔적 | fixture 로 양방향 |
| `tests/gates/testSelfLint.py` | README 와 specs 가 hanlint 의 error 지적을 받는 것 | 상투어가 든 문서로 잡히는지 본다 |
| `tests/gates/testNpmData.py` | `npm/data` 가 파이썬 정본의 투영과 다른 것 | 정본을 고치고 투영을 안 돌리면 red |
| `tests/gates/testNpmParity.py` | npm 구현이 파이썬과 다른 출력을 내는 것 | 규칙 하나를 한쪽만 고치면 red. node 없으면 건너뛴다 |
| `npm/test/rules.test.js` | npm 규칙이 같은 fixture 를 어기는 것. 규칙, fixture, 기술서, 파일의 넷이 짝인지 | fixture 로 양방향 |
| `hooks/tests/checkWriteGate.py` | 쓰기 훅의 판정 | 양방향 |

신설 게이트는 음성 시험으로 이빨을 증명하고서야 게이트다. 통과만 확인한 게이트는 없는 게이트보다 나쁘다.

## 자기 검사

이 저장소의 문서는 hanlint 자신이 검사한다. 설정은 루트 `hanlint.toml` 이고 참고 문서라 `noQuestion` 과
`readerAbsent` 만 끈다. 문서를 고쳤으면 `hanlint README.md` 로 먼저 본다.

## 실측

규칙을 더하거나 임계를 바꿨으면 실제 글에 돌려 오탐을 본다.

```powershell
hanlint 글.md --format json
hanlint audit 글.md
```

## 되돌리기

게이트가 틀렸으면 게이트와 그 fixture 를 같은 커밋에서 고친다. 게이트를 끄고 넘어가지 않는다.
