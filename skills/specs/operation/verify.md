---
id: operation.verify
title: 검증
category: operation
purpose: 커밋 전에 무엇을 돌리고 무엇을 통과해야 하는지 정한다. 게이트 목록과 각 게이트의 음성 시험도 여기 있다.
whenToUse:
  - 커밋 전에 뭘 돌리나
  - 게이트가 뭐가 있나
  - 테스트가 실패한다
  - 자기 검사가 왜 실패하나
verify:
  - .venv/Scripts/python.exe -X utf8 -B -m pytest -q
  - .venv/Scripts/python.exe -X utf8 -B -m ruff check src tests hooks scripts
  - .venv/Scripts/python.exe -X utf8 -B -m ruff format --check src tests hooks scripts
  - .venv/Scripts/python.exe -X utf8 -B scripts/derive/npmData.py --check
  - node --test npm/test/*.test.js
status: observed
---

# 검증

커밋 전에 아래 네 검사를 모두 통과해야 한다. `pre-push`가 pytest를 다시 돌린다. pytest 안에 npm 동등성 게이트가 있어
node가 있는 기계에서는 두 구현의 출력을 글자 단위로 비교한다.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest -q
.venv/Scripts/python.exe -X utf8 -B -m ruff check src tests hooks scripts
.venv/Scripts/python.exe -X utf8 -B -m ruff format --check src tests hooks scripts
node --test npm/test/*.test.js
```

`src/hanlint/data`나 규칙 docstring을 고쳤으면 `python scripts/derive/npmData.py`로 `npm/data`를 다시 만든다.
다시 만들지 않으면 `testNpmData`가 실패한다.

## 게이트

| 게이트 | 무엇을 막나 | 음성 시험 |
|---|---|---|
| `tests/rules/testRules.py` | 규칙이 fixture의 catch를 놓치거나 spare를 잡는 것 | fixture에 틀린 문장을 넣으면 실패한다 |
| `tests/rules/testRegistry.py` | 네 절 없는 규칙 docstring, 이름 어긋난 규칙 | 테스트 안에서 그런 규칙을 등록해 거부를 확인한다 |
| `tests/gates/testNaming.py` | snake_case 파일, 폴더, 함수, 변수 | 양성·음성 fixture |
| `tests/gates/testLayers.py` | 위 계층 import, 같은 계층끼리 import, 규칙끼리 import | 양성·음성 fixture |
| `tests/gates/testDash.py` | 추적 파일의 긴 줄표, 짧은 줄표 | 양성·음성 fixture |
| `tests/gates/testCommitMessage.py` | 커밋 메시지 형식, 빠진 검증 줄, 도구 흔적 | 양성·음성 fixture |
| `tests/gates/testSelfLint.py` | README와 specs가 hanlint의 오류 지적을 받는 것 | 상투어가 든 문서로 잡히는지 본다 |
| `tests/gates/testExemplars.py` | 예시 없는 규칙, before가 안 잡히거나 after가 잡히는 예시 | 규칙을 좁혀 before가 안 잡히게 하면 실패한다. 만들 때 일곱 개가 실제로 실패했다 |
| `tests/gates/testNpmData.py` | `npm/data`가 파이썬 기준 자료로 만든 사본과 다른 것 | 기준 자료를 고치고 사본을 다시 만들지 않으면 실패한다 |
| `tests/gates/testNpmParity.py` | npm 구현이 파이썬과 다른 출력을 내는 것. 지적 출력, `print`, `fix`, 규칙 목록과 설명서, 첫 화면, 폴더 인자, 프리셋별 `init` 파일 | 규칙이나 진입점을 한쪽만 고치면 실패한다. node가 없으면 건너뛴다 |
| `npm/test/rules.test.js` | npm 규칙이 같은 fixture를 어기는 것. 규칙, fixture, 설명서, 파일 넷이 짝인지 | 양성·음성 fixture |
| `tests/gates/testWriteGate.py` | 쓰기 훅 `hooks/writeGate.py`의 판정 | 양성·음성 입력 |
| `tests/gates/testPrimer.py` | `primer`에서 켜진 규칙이 빠지거나 겹치는 것, 고친 뒤 문장이 오류를 내는 것, 한 장이 100줄을 넘는 것 | 항목을 뺀 장과 고친 뒤 문장이 틀린 항목으로 둘 다 본다 |
| `.githooks/pre-push`의 `derive/profiles.py --check`, `derive/blueprints.py --check` | 말뭉치에서 다시 센 파생 자료가 커밋된 것과 다른 것. 말뭉치가 없는 기계는 건너뛴다고 말한다 | 코드를 바꾸고 파생 자료를 다시 만들지 않으면 실패한다. 2026-09-02에 profiles.json의 deixis 분포가 4일 낡은 채 잡혔다 |

새 게이트는 음성 시험으로 실제로 막는지 증명해야 게이트로 쓴다. 통과만 확인한 게이트는 막지 못하면서 막는다고 믿게 하므로 없는 것보다 나쁘다.

## 자기 검사

이 저장소의 문서는 hanlint 자신이 검사한다. 설정은 루트 `hanlint.toml`이고 참고 문서라 `preset = "docs"`
하나가 참고 문서에 맞지 않는 규칙을 끈다. 무엇이 꺼졌는지는 `hanlint doctor`가 답한다. 문서를 고쳤으면
`hanlint README.md`로 먼저 본다.

## 명령줄 밖 화면의 검증

명령줄 밖의 화면(GitHub Action, pre-commit, 지도 HTML, 평가 작업대 HTML)은 빌드 통과로 끝내지 않고 직접 실행해 확인한다.

- **GitHub Action.** ci의 `action` 잡이 루트 `action.yml`을 `uses: ./`로 자기 README 두 편에 실제로
  돌린다. push 뒤 `gh run watch`로 성공했는지 본다.
- **pre-commit.** 저장소 밖 작업 폴더의 venv에서 `pre-commit try-repo <저장소> hanlint --files 글.md`로 돌린다.
  try-repo는 추적 파일만 복제하므로 `.pre-commit-hooks.yaml`을 스테이징한 뒤라야 보인다. 틀린 글은
  1로, 지적이 없는 글은 0으로 끝나야 한다.
- **지도 HTML.** `hanlint map --format html` 산출물은 저장소 밖 작업 폴더의 pyproc으로 데스크톱 1440과
  모바일 390 스크린샷을 만들어 눈으로 본다. DOM 확인으로 끝내지 않는다. 범례 색이 0개로 나온 지도 버그는
  눈으로 본 검수에서 찾았다.
- **평가 작업대 HTML.** `hanlint arena review-page` 산출물은 `npm/package.json`과 `npm/package-lock.json`이 정한 정확한
  버전의 pyproc으로 실제 Chromium에서 확인한다. 고정 일곱 장르를 데스크톱 1440과 모바일 390에서 모두
  캡처해 눈으로 보고, 실제 라디오 버튼과 근거 입력, Alt+화살표 뒤 제목 초점, 창을 닫고 다시 연 뒤 진행 복원,
  7건 JSON 다운로드와 해시를 확인한다. 마지막에는 브라우저 자원(target, session, locator, artifact, transport)의 수가
  처음 값으로 돌아와야 한다.

## 실측

규칙을 더하거나 기준값을 바꿨으면 실제 글에 돌려 오탐을 본다.

```powershell
hanlint 글.md --format json
hanlint audit 글.md
```

## 되돌리기

게이트가 틀렸으면 게이트와 그 fixture를 같은 커밋에서 고친다. 게이트를 끄고 넘어가지 않는다.
