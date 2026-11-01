---
id: operation.sourceControl
title: 소스 관리
category: operation
purpose: 브랜치, 커밋 메시지, 커밋 단위, push, 릴리즈, 훅. 판정 기준은 hooks/commitMessage.py이고 이 문서는 뜻과 절차를 설명한다.
whenToUse:
  - 커밋 메시지를 어떻게 쓰나
  - 분류에 무엇을 적나
  - 훅이 커밋을 막았다
  - 릴리즈는 어떻게 하나
  - 새 클론에서 훅 켜기
verify:
  - .venv/Scripts/python.exe -X utf8 -B -m pytest tests/gates/testCommitMessage.py -q
  - git config core.hooksPath
status: curated
---

# 소스 관리

## 브랜치

`main` 전용이다. 로컬 브랜치와 worktree를 만들지 않는다. 원격 반영은 `main -> origin/main`과 릴리즈의
버전 태그 `v*`만 푸시한다. `.githooks/pre-push`가 다른 ref를 막는다. history 재작성과 force push는 명시 지시를
받고 한다.

## 커밋 메시지는 기록이다

릴리즈 노트, 사고 조사, 회귀 추적이 전부 커밋 메시지에 기댄다. 제목 한 줄만 남기면 이력은 라벨 모음이
되고 여섯 달 뒤 왜 그랬는지를 코드에서 재구성해야 한다.

```text
분류: 무엇을 했는지 한 줄 요약

무엇을 어떻게 바꿨는지 (파일과 심볼 수준).
왜 필요했는지 (문제와 근거. 되돌리려는 사람이 판단할 수 있게).
검증: 어느 게이트가 green 인지. 신설 게이트면 음성 시험 결과까지.
```

- 한국어로 쓴다. 제목은 `분류: 요약` 꼴로 72자 이내이고 마침표를 찍지 않는다. 분류는 16자 이내다.
- 본문은 반드시 쓴다. 제목과 빈 줄로 나누고 최소 2줄, 80자 이상, 줄당 100자 이내로 쓴다.
- **검증 줄은 반드시 쓴다.** 무엇으로 확인했는지 없는 변경은 기록이 아니라 주장이다. 게이트가 없는 문서 커밋은
  `검증: 게이트 없음. 문서만.`이라고 정직하게 적는다.
- 도구와 생성 흔적을 넣지 않는다. 판정기가 막는다.
- 긴 줄표(U+2014)를 넣지 않는다.
- `git`이 스스로 만드는 제목(Merge, Revert, fixup)은 형식 검사 밖이고 흔적 검사만 남는다.

판정 기준은 `hooks/commitMessage.py`이고 `.githooks/commit-msg`가 부른다. 훅은 판정기를 부르기만 한다. 판정을 sh와
파이썬에 따로 두면 두 판정이 서로 달라진다. `tests/gates/testCommitMessage.py`가 양성·음성 fixture로
판정기가 실제로 막는지 실행할 때마다 증명한다.

### 분류

| 분류 | 언제 |
|---|---|
| `체계` | 저장소 뼈대, 규칙 문서, 훅, 설정 |
| `코어` | document, analysis, fingerprint, config, report, cli |
| `규칙` | rules와 fixture. 규칙 하나가 커밋 하나인 것이 보통이다 |
| `분석` | audit, profile |
| `게이트` | tests/gates와 훅의 판정 |
| `문서` | README, specs, 스킬 |
| `수리` | 버그 수정. 무엇이 어떻게 깨졌는지 본문에 적는다 |
| `릴리즈` | 버전과 태그. 명시 지시가 있을 때만 |

## 커밋 단위

한 작업에 여러 의도가 섞이면 의도별로 나눈다. `git add .`과 `git add -A`를 쓰지 않는다. 관련 경로만
골라 스테이징한다. `pytest`와 게이트를 모두 통과했을 때만 커밋한다. 통과하지 못하면 올리지 않고 왜 막혔는지
보고한다.

## 릴리즈

`0.0.x` 라인에서 명시 지시가 있을 때만 한다. 버전을 1 올리는 변경과 태그 `v0.0.x`를 같은 커밋에 둔다. 버전의 기준은
`src/hanlint/__init__.py`의 `__version__`이고 태그와 항상 같은 값이다. 체인지로그의 기준은 루트
`CHANGELOG.md`이다. 릴리즈 메시지는 제목과 버전 절의 CHANGELOG 본문을 한 검토 파일에 둔다. 주석
태그(annotated tag)는 Markdown 제목을 보존하는 정리 방식으로 그 파일을 읽고 GitHub Release도 같은 본문을 쓴다. 전체
배포 절차는 `operation.release`가 기준이다.

## 훅

`.githooks/`에 셋이 있다.

| 훅 | 무엇을 막나 |
|---|---|
| `commit-msg` | 메시지 형식, 빠진 검증 줄, 도구 흔적, 긴 줄표 |
| `pre-commit` | 스테이징한 텍스트 파일의 긴 줄표와 짧은 줄표와 제어 문자, `src` `tests` `hooks` `scripts` `npm` `web` 아래 snake_case 코드 파일 이름 |
| `pre-push` | main과 버전 태그(v*)가 아닌 ref, 태그 이름과 그 커밋 `__version__`의 불일치, `pytest` 실패, 말뭉치가 있는 기계에서 파생 자료(`profiles.json`, `blueprints.json`)가 코드와 어긋난 것 |

새 클론에서 한 번 한다. 개발 환경은 `uv sync` 하나가 만든다. `uv.lock`이 정확한 버전을 고정하고 `.venv/`에 설치한다.
pip로 따로 설치하지 않는다.

```powershell
uv sync
git config core.hooksPath .githooks
```

훅이 막으면 우회하지 않는다 (`--no-verify` 금지). 막힌 이유를 고친다. 훅 자체가 틀렸으면 판정기와 그
테스트를 같은 커밋에서 고친다.

## Claude 훅

`.claude/settings.json`이 `hooks/writeGate.py`를 Write, Edit 앞에 건다. snake_case 파일 이름과 긴 줄표와
저장소 안 임시 산출물 경로를 쓰기 전에 막는다. 자기 검사는 `tests/gates/testWriteGate.py`다.
`settings.json`은 로컬 상태가 아니라 꼭 지킬 계약이라 git으로 추적한다.

## 되돌리기

잘못 들어간 커밋은 `git revert`로 되돌린다. 되돌리는 커밋도 같은 형식이다.
