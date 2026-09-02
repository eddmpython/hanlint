---
id: skills.README
title: hanlint Skill OS
category: start
purpose: 이 저장소의 운영 정본 진입점. 무엇을 만들고 무엇을 만들지 않으며 어떻게 넓히는지 여기서 찾는다.
whenToUse:
  - hanlint 가 뭔가
  - 규칙을 어떻게 더하나
  - 무엇을 잡고 무엇을 안 잡나
  - 어디를 봐야 하나
status: curated
---

# hanlint Skill OS

지금 실제로 도는 구조와 절차의 정본이다. 여기 없는 절차는 아직 없는 것이다.

## 정보가 있는 곳

같은 사실을 두 곳에 쓰지 않는다.

| 층 | 내용 | 위치 |
|---|---|---|
| 강행규칙 | 위반하면 제품이나 이력이 망가지는 것 | 루트 `CLAUDE.md` (추적하지 않음) |
| 운영 정본 | 경계, 절차, 계약. 기계가 강제하는 것 | **`skills/specs/`** |
| 사용 스킬 | AI 가 hanlint 로 검사하거나 글을 쓰는 절차 | `skills/use-hanlint/`, `skills/write-korean/` |
| 끝나지 않은 기획 | 이니셔티브 | `mainPlan/` (추적하지 않음) |
| 규칙의 근거 | 실측 사례와 판정 기준 | 그 규칙 파일의 docstring |

`README.md` 는 바깥을 향한 소개다. 운영 절차를 거기에 복제하지 않는다.

## 카테고리

| 카테고리 | 위치 | 의미 |
|---|---|---|
| `start` | `specs/start/` | 처음 여는 사람이 먼저 읽는 것. 경계 |
| `operation` | `specs/operation/` | 규칙 추가, 층 구조, 검증, 배포 |

없는 카테고리를 미리 만들지 않는다.

## 스킬

id 가 경로다. 표에 없는 절차는 아직 없는 것이다.

| id | 무엇 |
|---|---|
| [`start.hanlintSkillOs`](specs/start/hanlintSkillOs.md) | 이 저장소가 소유하는 것과 어디로 가야 하는지 |
| [`start.product`](specs/start/product.md) | 무엇을 잡고 무엇을 잡지 않는가. 평가 루프에서의 자리 |
| [`start.readerContract`](specs/start/readerContract.md) | 모델 독립적 Contract, Finding, Patch와 결정적 영수증 프로토콜 |
| [`operation.addingARule`](specs/operation/addingARule.md) | 규칙을 더하고 고치고 빼는 절차 |
| [`operation.moduleLayers`](specs/operation/moduleLayers.md) | 층 구조와 import 방향. 순위 정본은 `tests/gates/layerContract.py` |
| [`operation.codeStyle`](specs/operation/codeStyle.md) | 이름, 크기, 타입, docstring, 예외, 상수, 테스트, 도구 |
| [`operation.sourceControl`](specs/operation/sourceControl.md) | 브랜치, 커밋 메시지, 커밋 단위, 릴리즈, 훅 |
| [`operation.verify`](specs/operation/verify.md) | 커밋 전에 돌리는 게이트와 각 게이트의 음성 시험 |
| [`operation.release`](specs/operation/release.md) | PyPI 와 npm 에 같은 버전을 올리는 절차 |
| [`operation.feedback`](specs/operation/feedback.md) | 오탐과 미탐과 제안을 받는 길 |
| [`operation.writingAxis`](specs/operation/writingAxis.md) | 보류 중인 작문 축 (brief, guard, packet, arena, learn) 의 절차 |
| [`use-hanlint`](use-hanlint/SKILL.md) | 이미 쓴 글의 결정적 지적을 fix 와 후보로 0 으로 만들고 평가로 넘기는 일곱 단계 |
| [`write-korean`](write-korean/SKILL.md) | primer 를 읽고 절마다 검사하며 처음부터 쓰는 다섯 단계 |

## 스킬 추가

`SCHEMA.md` 를 따른다.
