---
id: operation.release
title: 배포
category: operation
purpose: PyPI 와 npm 에 같은 버전을 올리는 절차. GitHub Actions 가 집행하고 사람은 태그만 민다. 릴리즈는 명시 지시가 있을 때만 한다.
whenToUse:
  - 배포하고 싶다
  - 버전을 올리나
  - PyPI 와 npm 에 어떻게 올라가나
  - 처음 한 번 무엇을 설정하나
  - 깨끗한 환경에서 설치가 되나
verify:
  - .venv/Scripts/python.exe -X utf8 -B -m pytest -q
status: curated
---

# 배포

`0.0.x` 라인에서 명시 지시가 있을 때만 릴리즈한다. 일상 커밋은 버전과 태그를 건드리지 않는다. 집행은
`.github/workflows/publish.yml` 이고 인증은 PyPI 와 npm 둘 다 Trusted Publishing (OIDC) 이다. 장수 토큰
시크릿을 저장소에 두지 않는다.

## 처음 한 번 (운영자)

1. **PyPI.** pypi.org 에 로그인해 Account settings > Publishing > Add a new pending publisher. 값은 다음과 같다.
   PyPI project name `hanlint`, Owner `eddmpython`, Repository name `hanlint`, Workflow name `publish.yml`,
   Environment name `pypi`. 프로젝트가 아직 없어도 pending publisher 로 등록되고 첫 게시가 프로젝트를 만든다.
2. **GitHub.** 저장소 Settings > Environments > New environment 로 `pypi` 를 만든다. 원하면 Required
   reviewers 에 자신을 넣어 게시 직전에 한 번 더 승인하게 둔다.
3. **npm 첫 게시.** npm 의 Trusted Publisher 는 이미 있는 패키지의 Settings 에서만 등록할 수 있다. 그래서
   첫 판 (0.0.1) 은 운영자 기계에서 올린다. `npm login` 뒤 `cd npm && npm publish`. 2FA 가 켜져 있으면
   OTP 를 묻는다.
4. **npm Trusted Publisher.** 패키지가 생기면 npmjs.com > hanlint > Settings > Trusted Publisher >
   GitHub Actions 에 Repository `eddmpython/hanlint`, Workflow `publish.yml` 을 등록한다. 다음 태그부터
   Actions 가 올린다.

## 릴리즈 커밋

버전 +1 과 태그 `v0.0.x` 를 같은 커밋에. 버전을 손으로 적는 곳은 `src/hanlint/__init__.py` 의
`__version__` 과 `npm/package.json` 둘뿐이다. `pyproject.toml` 은 hatch 가 `__version__` 을 읽고 (dynamic),
`npm/data/version.json` 은 투영이라 `python scripts/exportData.py` 를 같은 커밋에서 돌린다.
`npm/package-lock.json`도 `npm install --package-lock-only --ignore-scripts`로 갱신하는 투영이다. 워크플로가
`__version__`, `package.json`, 태그를 대조하고 `tests/gates/testVersion.py` 가 로컬에서 버전 투영까지 강제한다.
0.0.2 에서 pyproject 만 올리고 `__version__` 을 빼먹어 `--version` 이 낡은 채 게시된 것이 이 구조의 이유다.

체인지로그의 정본은 루트 `CHANGELOG.md` (Keep a Changelog 형식) 다. 변경은 `[Unreleased]` 에 쌓고 릴리즈
커밋에서 그 내용을 `[X.Y.Z] - 날짜` 절로 내린다. `git log v이전판..HEAD`의 공개 변경이 이 절에 모두
분류됐는지 검토한다. 내부 작업을 공개 노트에서 뺄 때도 누락으로 두지 않고 검토 기록에 제외 이유를 남긴다.

릴리즈 메시지는 제목 `hanlint X.Y.Z 요약`과 그 버전의 CHANGELOG 본문을 한 임시 파일에 둔다. annotated
tag는 이 파일을 `--cleanup=verbatim -F`로 읽는다. 기본 정리 방식은 `###` 제목을 주석으로 보고 지우므로
쓰지 않는다. 배포 워크플로도 tag 객체에서 같은 본문을 꺼내 GitHub Release의 `body_path`로 쓴다. 태그와
공개 노트가 서로 다른 이력을 만들지 않는다.

```powershell
# src/hanlint/__init__.py 의 __version__ 과 npm/package.json 의 version 을 올리고
# CHANGELOG 의 Unreleased 를 버전 절로 내리고 정확한 Git 범위를 대조한 뒤
.venv/Scripts/python.exe -X utf8 -B scripts/exportData.py
Push-Location npm
npm install --package-lock-only --ignore-scripts
Pop-Location
.venv/Scripts/python.exe -X utf8 -B -m pytest -q
git add src/hanlint/__init__.py npm/package.json npm/package-lock.json npm/data/version.json CHANGELOG.md
git commit -F 메시지파일
git status --short   # tracked 수정이 남아 있으면 커밋에 빠진 파일이 있는 것이다. 비기 전에는 태그를 만들지 않는다
git tag -a v0.0.x --cleanup=verbatim -F 릴리즈메시지파일
git push origin main v0.0.x
```

0.0.6 이 이 확인의 이유다. 버전 일원화 파일 (pyproject, publish.yml, 버전 게이트) 이 로컬에만 있고
커밋에서 빠진 채 태그가 나가, CI 의 옛 대조 스크립트가 옛 pyproject 를 읽고 게시를 막았다.

## 워크플로가 하는 일

1. `ci.yml` 의 게이트 전부 (세 운영체제와 파이썬 조합, ruff, pytest, npm 테스트, 투영 검사, 쓰기 훅 자기 검사).
2. 세 버전 일치 검증. wheel 과 sdist 빌드. 그 wheel 을 격리 venv 에 설치해 Requires 가 비어 있는지, 데이터가
   동봉됐는지, `hanlint README.md` 가 통과하는지 본다.
3. `publish-pypi` (environment `pypi`, OIDC) 와 `publish-npm` (OIDC, npm 11 이상) 이 나란히 올린다.
4. annotated tag의 검토된 메시지를 본문으로 쓰고 GitHub Release에 wheel과 sdist를 붙인다.

## 올린 뒤

빈 폴더에서 두 표면을 받아 같은 출력인지 본다.

```powershell
python -X utf8 -B -m venv C:/Users/MSI/AppData/Local/dev-workspace/hanlintInstall
C:/Users/MSI/AppData/Local/dev-workspace/hanlintInstall/Scripts/pip install hanlint==0.0.x
C:/Users/MSI/AppData/Local/dev-workspace/hanlintInstall/Scripts/hanlint README.md --format json
npx hanlint@0.0.x README.md --format json
```

끝나면 그 venv 를 지운다.

## 되돌리기

PyPI 는 같은 버전을 다시 올릴 수 없다. 잘못 올렸으면 그 버전을 yank 하고 다음 버전으로 고친다. npm 은
72시간 안이면 `npm unpublish hanlint@0.0.x` 가 되고 그 뒤에는 `npm deprecate` 로 표시한다. 워크플로가
중간에 실패했으면 원인을 고친 커밋에 새 태그를 붙인다. 같은 태그를 옮기지 않는다.
