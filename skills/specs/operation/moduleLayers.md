---
id: operation.moduleLayers
title: 모듈 계층 구조와 import 방향
category: operation
purpose: 코드가 어느 폴더에 살고 무엇을 import해도 되는지 정한다. 순위의 기준은 tests/gates/layerContract.py이고 이 문서는 뜻과 판단을 설명한다.
whenToUse:
  - 이 파일을 어느 폴더에 두나
  - 이 import가 허용되나
  - 규칙 파일끼리 왜 import 못 하나
  - 새 계층을 만들어도 되나
verify:
  - .venv/Scripts/python.exe -X utf8 -B -m pytest tests/gates/testLayers.py -q
status: curated
---

# 모듈 계층 구조와 import 방향

**계층은 폴더와 같고 import는 아래로만 한다.** 모든 import가 아래 계층을 향하므로 순환이 생기지 않는다. 순위의 기준은
`tests/gates/layerContract.py`이고 `tests/gates/testLayers.py`가 검사한다. 여기에 숫자를 옮겨 적지 않는다.

## 계층의 뜻

| 계층 | 무엇 | 아래에 무엇을 두나 |
|---|---|---|
| `util`(npm만) | 루트의 `text.js`, `regex.js`. 파이썬 `str`과 `re`의 뜻 | 아무것도 |
| `data` | 사전과 접속사 목록. 코드는 없다 | 아무것도(npm은 util) |
| `config` | 설정과 기본 기준값 | 아무것도 |
| `document`, `blueprint`, `evidence`, `entailment` | 문서 모델 / 원문 없는 구조 예산 / 사실별 근거 기록 / 외부 함의 평가기 벤치마크 | config / config, data / config / data |
| `analysis` | 글자 모양 분석(문장 분리, 어절 판정)과, 어절 판정과 무관한 한국어 형태 부분(grammar). 문서 모델을 모른다 | config, data |
| `fingerprint` | 문장·문단·절·글에서 센 값을 적은 분석표. 사전에 맞은 곳도 담는다 | document, analysis, config, data |
| `usage` | 용례. 글 종류별 명사 연쇄 빈도표(실린다)와 문장 역인덱스(사용자 기계). fingerprint와 같은 계층 | analysis, config, data |
| `rules`, `audit`, `profile` | 분석표를 읽는 같은 계층의 셋. 서로 import하지 않는다 | fingerprint, usage와 그 아래 |
| `report`, `edit`, `coverage`, `baseline`, `learn`, `guard` | Finding과 분석표를 보고서, 파일, 고침 후보와 사실 계약 결과로 옮기는 여섯 모듈. 서로 import하지 않는다 | rules, audit, profile과 그 아래 |
| `arena` | 두 생성 결과를 guard로 본 안전성과 블라인드 사람 평가의 선호를 따로 집계하는 글쓰기 비교 | guard와 그 아래 |
| `cli` | 명령 | 전부 |

npm 구현(`npm/src/`)은 같은 폴더와 같은 순위를 그대로 따르고 같은 게이트가 import 방향을 본다. npm에만
루트 도우미 계층 `util`(`text.js`, `regex.js`)이 있다. JS에서 파이썬 `str`과 `re`의 뜻을 똑같이 맞추는 계층이라
`data`보다도 아래다. `index.js`는 `__init__.py`처럼 계층이 아니라 공개 API다.

`src/hanlint/__init__.py`는 계층이 아니라 공개 API다. report와 rules와 fingerprint를 모아 밖에 낸다.
패키지 밖에서 내부 경로를 직접 import하게 두지 않는다.

**이름 목록은 여기 적지 않는다.** 기준은 `src/hanlint/__init__.py`의 `__all__` 하나이고 지금 무엇이
나가는지는 `python -c "import hanlint; print(sorted(hanlint.__all__))"`가 말한다. 2026-08-31 이전에는
이 문서에 열일곱 개를 손으로 옮겨 두었고, 그 사이 실제 공개 이름이 일흔 개로 늘어 문서가 사실과 어긋났다.

## 규칙 파일의 격리

`rules/<묶음>/<규칙>.py`는 규칙 목록에 자기를 등록할 뿐 **다른 규칙을 import하지 않는다.** 공통 로직은
`rules/shared/`에 둔다. 규칙이 규칙을 부르기 시작하면 하나를 끄는 순간 다른 것이 깨진다.

## 왜 형제를 막나

rules와 audit과 profile은 같은 분석표를 읽어 쓰는 셋이다. 하나가 다른 하나를 부르면 "분석표 → 읽는 쪽"이라는
한 방향이 깨지고, audit을 끄고 싶은 사용자가 rules까지 잃는다. 공유할 것이 생기면 fingerprint로 내린다.

## 새 계층

새 계층은 거기에 둘 코드가 실제로 생겼을 때 `layerContract.py`에 한 줄 더하고 이 표에 뜻을 적는다. 미리 만들지
않는다. `codeRun`(코드 블록 실행 검증)이 나중에 rules와 같은 계층에 들어올 후보다.

## 되돌리기

계층을 잘못 나눴으면 폴더를 옮기고 `layerContract.py`를 고친다. 게이트가 import 방향을 다시 본다.
