---
id: start.integrations
title: 자동화 연결
category: start
purpose: 소비 저장소에서 GitHub Actions, pre-commit과 에이전트에 hanlint를 연결하는 예제를 소유한다.
whenToUse:
  - PR에서 문서를 검사한다
  - 커밋 전 검사를 설정한다
  - AI의 파일과 답변을 검사한다
status: curated
---

# 자동화 연결

[처음으로](../../../README.md) · [명령과 설정](cli.md) · [브라우저 편집기](https://eddmpython.github.io/hanlint/)

자동화에는 팀이 고른 프리셋과 예외를 `hanlint.toml`로 커밋한다. 먼저 같은 파일을 로컬에서 검사해
적용할 규칙을 확인한다. 기존 지적을 제외하려면 [baseline을 설정](cli.md#기존-문서에-도입하기)한다.

## GitHub Actions에서 검사하기

소비 저장소의 `.github/workflows/hanlint.yml`에 다음 내용을 넣는다. `docs/`는 검사할 경로로 바꾼다.

```yaml
name: Korean prose
on: [push, pull_request]
permissions:
  contents: read
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: 22
      - uses: eddmpython/hanlint@v0.0.10
        with:
          files: docs/
          errors-only: "true"
          command: npx --yes hanlint@0.0.10
```

예제는 액션과 검사 패키지를 같은 릴리즈에 고정한다. 갱신할 때 둘을 함께 바꾼다. 입력 계약은
루트 [action.yml](../../../action.yml)이 소유한다. Action은 지적을 GitHub 줄 주석으로 출력하고 error가
있으면 실패한다. PR에 별도 댓글을 게시하거나 원고를 자동 수정하지 않는다.

`files`는 공백으로 구분한 파일 또는 폴더 경로다. 이 입력으로 공백이 든 파일 이름을 정확히 구분할 수
없으므로, 그런 문서는 공백 없는 상위 폴더를 대상으로 검사한다.

## 커밋 전에 검사하기

pre-commit을 사용하는 저장소의 `.pre-commit-config.yaml`에 추가한다.

```yaml
repos:
  - repo: https://github.com/eddmpython/hanlint
    rev: v0.0.10
    hooks:
      - id: hanlint
```

```console
pre-commit install
pre-commit run hanlint --all-files
```

훅은 변경된 마크다운을 검사하며 기본 인자는 error만 표시하는 `--errors-only --quiet`다.
검사기가 파일을 고치지는 않는다. 공개 훅의 정의는 [.pre-commit-hooks.yaml](../../../.pre-commit-hooks.yaml)에 있다.
이 저장소를 개발할 때 쓰는 `.githooks/`와는 용도가 다르다.

## 에이전트에 지적 전달하기

도구를 실행할 수 있는 에이전트에는 검사 결과 JSON을 전달한다.

```console
hanlint 글.md --format json
```

[`use-hanlint`](../../use-hanlint/SKILL.md)는 이미 쓴 글을 검사하고 고치는 절차다.
[`write-korean`](../../write-korean/SKILL.md)은 글을 쓰면서 같은 규칙을 확인하는 절차다.
스킬을 쓰는 제품의 설치 방식에 맞춰 연결한다. 자동화에서도 사실과 뜻, 독자의 과업은 사람이 확인한다.

## Claude Code의 저장·답변 훅

`hanlint hook`은 PostToolUse 입력에서 `Write` 또는 `Edit`가 저장한 마크다운 한 파일을 검사한다.
`hanlint hook --reply`는 Stop 입력의 마지막 답변을 `chat` 프리셋으로 검사한다.
지적이 있을 때만 다음 요청의 문맥으로 전달하며, 검사 명령은 항상 종료 코드 0으로 끝난다.

`uvx`가 설치된 환경에서는 `.claude/settings.json`의 기존 설정에 다음 항목을 합친다.
아래 예제로 파일 전체를 덮어쓰면 기존 훅을 잃을 수 있으므로 PostToolUse와 Stop 배열에 추가한다.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "uvx", "args": ["hanlint", "hook"] }]
      }
    ],
    "Stop": [
      {
        "hooks": [{ "type": "command", "command": "uvx", "args": ["hanlint", "hook", "--reply"] }]
      }
    ]
  }
}
```

Node의 `npx`를 쓰면 각 훅 항목을 다음 셸 형식으로 바꾼다. Windows의 `npx.cmd`도 실행할 수 있도록
`args`를 따로 두지 않는다.

```json
{ "type": "command", "command": "npx --yes hanlint hook" }
```

Stop 항목은 `command`를 `npx --yes hanlint hook --reply`로 바꾼다. 정확한 버전을 유지해야 하는
프로젝트는 패키지 버전도 고정한다. 입력·출력과 실행 형식은 [Claude Code 공식 훅 문서](https://code.claude.com/docs/en/hooks#command-hook-fields)를 따른다.

저장 훅은 저장한 파일에서 찾은 저장소 설정과 baseline을 사용한다. 답변 훅은 같은 설정에서 프리셋을
`chat`으로 바꾼다. `stop_hook_active` 재진입에는 결과를 내지 않는다. 깨진 입력이나 읽을 수 없는 파일은
검사를 생략하므로, 파일을 반드시 검사해야 하는 발행 단계에는 일반 CLI나 CI 검사를 함께 사용한다.

## 편집기를 내 계정에 배포하기

브라우저는 GitHub Pages에서 정적 파일로 동작한다. 사용자용 [Fork 안내](https://eddmpython.github.io/hanlint/guide.html#fork)에
따라 사이트를 운영할 수 있다. 사이트 소스와 원고용 저장소의 역할, 저장과 공개 범위도 그 안내에서 확인한다.
개발자의 로컬 실행과 배포 절차는 [브라우저 편집기 운영](../operation/webEditor.md)이 소유한다.
