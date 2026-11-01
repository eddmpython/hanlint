---
id: start.hanlintSkillOs
title: 이 저장소가 맡는 것
category: start
purpose: 이 저장소의 경계와 구성, 그리고 어디로 가야 무엇이 있는지 알려준다.
whenToUse:
  - 이 저장소는 뭐하는 곳인가
  - 어디를 봐야 하나
  - 경계
  - 폴더 구조
  - cinch와 어떻게 맞물리나
status: curated
---

# 이 저장소가 맡는 것

## 맡는 것

한국어 글 린터 hanlint의 Python 패키지와 CLI, npm 패키지, 브라우저 편집기와 AI 사용 스킬이다.

| 경로 | 무엇 |
|---|---|
| `src/hanlint/` | Python 패키지. 모듈 계층 구조는 `operation.moduleLayers`가 기준이다 |
| `npm/` | Python 패키지를 옮긴 구현. 순수 ESM이고 빌드 단계가 없다. `npm/src`가 제품, `npm/test`가 테스트, `npm/data`는 `scripts/derive/npmData.py`가 만든다 |
| `web/` | 같은 npm 엔진을 쓰는 브라우저 편집기, 개인 기록, GitHub 보관과 사용 안내. 정적 배포는 `operation.webEditor`가 맡는다 |
| `tests/` | 잡아야 할 글과 넘겨야 할 글을 함께 보는 테스트와 구조 게이트. `tests/_attempts/`는 실험 기록 |
| `hooks/` | 훅 판정기. `writeGate.py`는 Claude 쓰기 훅이, `commitMessage.py`는 git commit-msg 훅이 부른다. 얇은 셸은 `.githooks/`, 등록은 `.claude/settings.json` |
| `scripts/` | 도구 스크립트. 세 폴더로 나뉜다. `derive/`는 기준 자료에서 파생 자료를 만들고, `fetch/`는 외부 자료를 받고, `measure/`는 실측 실험 스크립트다 |
| `corpus/` | 기준 말뭉치의 카탈로그와 고정한 버전. 원문은 `catalogue.toml`의 `root`(`~/.cache/hanlint/corpus/`)에 받는다 |
| `skills/` | 운영 기준 문서와 AI 사용 스킬 |
| `.cinch.json` | cinch 설정. 켠 스위치와 코드 폴더의 역할을 적는다. 설치된 Stop 게이트가 판정하고 `cinch status`가 보여 준다 |
| `mainPlan/` | 끝나지 않은 기획(추적하지 않음) |
| `memory/` | 세션 사이에 이어 가는 메모(추적하지 않음) |

## 맡지 않는 것

- **글의 좋고 나쁨.** 판정은 사람과 LLM 평가자가 한다. hanlint는 세어서 확실히 알 수 있는 결함만 짚는다
- **글쓰기 규칙의 기준.** 어떤 글이 좋은 글인지는 hanlint를 쓰는 저장소의 글쓰기 스킬이 정한다. hanlint는 그 가운데
  기계가 잡을 수 있는 것을 검사할 뿐이다. 그 저장소가 어떤 규칙을 켤지는 그 저장소의 설정이 정한다
- **맞춤법.** 공식 API 없이 비공식 스크래핑에 기대는 검사기는 넣지 않는다

## 어디로 가나

묻는 것에 따라 여는 문서가 다르다.

| 알고 싶은 것 | 어디 |
|---|---|
| 어기면 사고가 나는 규칙 | 루트 `CLAUDE.md`(추적하지 않음) |
| 무엇을 잡고 무엇을 안 잡나 | [`start.product`](product.md) |
| 첫 검사와 프로젝트 설정 | [`start.cli`](cli.md) |
| CI와 에이전트 연결 | [`start.integrations`](integrations.md) |
| 브라우저에서 글을 고치고 기록하는 법 | [사용과 저장 안내](https://eddmpython.github.io/hanlint/guide.html) |
| 브라우저 편집기 실행과 Pages 배포 | [`operation.webEditor`](../operation/webEditor.md) |
| 규칙을 더하는 법 | `operation.addingARule` |
| 커밋 전에 돌릴 것 | `operation.verify` |
| 배포 절차 | `operation.release` |
| 규칙 목록 | `hanlint rules` |
| AI에게 글을 쓰게 하는 법 | `skills/write-korean/SKILL.md` |
| AI에게 검사를 시키는 법 | `skills/use-hanlint/SKILL.md` |
| 바깥을 향한 소개 | 루트 `README.md` |
| 지금 진행 중인 기획 | `mainPlan/` |

## cinch 문서 역할과의 대응

cinch는 저장소 문서를 여섯 역할로 읽는다. 이 저장소는 새 문서 폴더를 만들지 않고, 있는 문서를 그 역할에 맞춘다.

| cinch 역할 | 이 저장소의 기준 문서 |
|---|---|
| North Star | [`start.product`](product.md) |
| 기술 명세 | [`start.readerContract`](readerContract.md), `operation.moduleLayers`, 코드 계약(`tests/gates/layerContract.py`, `src/hanlint/data/*.schema.json`) |
| 운영 명세 | `skills/specs/operation/` |
| 이니셔티브 | `mainPlan/`(추적하지 않음. 끝나면 폴더째 지운다) |
| 세션 메모리 | `memory/`(추적하지 않음. 기준 문서를 덮지 않는다) |
| 이벤트 기록 | Git 커밋. 형식은 `operation.sourceControl` |

## 이 저장소가 실패하는 경우

규칙이 늘어날 때다. 그럴듯한 규칙은 오탐을 낳고 오탐은 첫인상을 망친다. 그래서 실측 사례
없는 규칙을 넣지 않고, 사람 평가자가 짚은 지적 가운데 hanlint가 먼저 짚었던 비율로 가치를 잰다.
규칙 수는 가치가 아니다.
