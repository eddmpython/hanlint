---
id: operation.moduleLayers
title: 층 구조와 import 방향
category: operation
purpose: 코드가 어느 폴더에 살고 무엇을 import 해도 되는지 정한다. 순위의 정본은 tests/gates/layerContract.py 이고 이 문서는 뜻과 판단을 설명한다.
whenToUse:
  - 이 파일을 어느 폴더에 두나
  - 이 import 가 허용되나
  - 규칙 파일끼리 왜 import 못 하나
  - 새 층을 만들어도 되나
verify:
  - .venv/Scripts/python.exe -X utf8 -B -m pytest tests/gates/testLayers.py -q
status: curated
---

# 층 구조와 import 방향

**층 = 폴더. import 는 아래로만.** 모든 edge 가 순위를 낮추므로 순환은 불가능하다. 순위의 정본은
`tests/gates/layerContract.py` 이고 `tests/gates/testLayers.py` 가 집행한다. 여기에 숫자를 옮겨 적지 않는다.

## 층의 뜻

| 층 | 무엇 | 아래에 무엇을 두나 |
|---|---|---|
| `util` (npm 만) | 루트의 `text.js`, `regex.js`. 파이썬 `str` 과 `re` 의 뜻 | 아무것도 |
| `data` | 사전과 표지 목록. 코드 없음 | 아무것도 (npm 은 util) |
| `config` | 설정과 임계 기본값 | 아무것도 |
| `document`, `blueprint`, `evidence`, `entailment` | 문서 모델 / 원문 없는 구조 예산 / 사실별 근거 원장 / 외부 함의 평가기 benchmark | config / config, data / config / data |
| `analysis` | 표층 분석 (문장 분리, 어절 판정) 과 어절 판정과 무관한 한국어 형태 층 (grammar). 문서 모델을 모른다 | config, data |
| `fingerprint` | 문장·문단·절·글 지문. 사전 매치 포함 | document, analysis, config, data |
| `rules`, `audit`, `profile` | 지문 위의 세 형제. 서로 import 하지 않는다 | fingerprint 와 그 아래 |
| `report`, `edit`, `coverage`, `baseline`, `learn`, `guard` | Finding 과 지문을 보고서, 파일, 고침 후보와 사실 계약 결과로 옮기는 여섯 층. 서로 import 하지 않는다 | rules, audit, profile 과 그 아래 |
| `arena` | 두 생성 결과의 guard 안전성과 블라인드 사람 선호를 분리하는 작법 대조 | guard 와 그 아래 |
| `cli` | 명령 | 전부 |

npm 구현 (`npm/src/`) 은 같은 폴더와 같은 순위를 거울처럼 따르고 같은 게이트가 import 방향을 본다. npm 에만
루트 도우미 층 `util` (`text.js`, `regex.js`) 이 있다. 파이썬 `str` 과 `re` 의 뜻을 JS 에서 같게 드는 자리라
`data` 보다도 아래다. `index.js` 는 `__init__.py` 처럼 층이 아니라 공개 표면이다.

`src/hanlint/__init__.py` 는 층이 아니라 공개 표면이다. report 와 rules 와 fingerprint 를 모아 밖에 낸다.
패키지 밖에서 deep-path를 import 하게 두지 않는다.

**이름 목록은 여기 적지 않는다.** 정본은 `src/hanlint/__init__.py` 의 `__all__` 하나이고 지금 무엇이
나가는지는 `python -c "import hanlint; print(sorted(hanlint.__all__))"` 가 말한다. 2026-08-31 이전에는
이 자리에 열일곱 개를 손으로 베껴 두었고, 그 사이 실제 표면이 일흔 개로 늘어 문서가 사실과 어긋났다.

## 규칙 파일의 격리

`rules/<부류>/<규칙>.py` 는 등록부에 자기를 등록할 뿐 **다른 규칙을 import 하지 않는다.** 공통 로직은
`rules/shared/` 에 둔다. 규칙이 규칙을 부르기 시작하면 하나를 끄는 순간 다른 것이 깨진다.

## 왜 형제를 막나

rules 와 audit 와 profile 은 같은 지문을 읽는 세 소비자다. 하나가 다른 하나를 부르면 "지문 → 소비자" 라는
한 방향이 깨지고, audit 를 끄고 싶은 사용자가 rules 까지 잃는다. 공유할 것이 생기면 fingerprint 로 내린다.

## 새 층

새 층은 그 표면이 실제로 생겼을 때 `layerContract.py` 에 한 줄 더하고 이 표에 뜻을 적는다. 미리 만들지
않는다. `codeRun` (코드 블록 실행 검증) 이 M2 이후 rules 의 형제로 들어올 후보다.

## 되돌리기

층을 잘못 나눴으면 폴더를 옮기고 `layerContract.py` 를 고친다. 게이트가 import 방향을 다시 본다.
