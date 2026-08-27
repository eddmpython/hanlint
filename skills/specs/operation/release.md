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

버전 +1 과 태그 `v0.0.x` 를 같은 커밋에. `pyproject.toml` 의 version, `npm/package.json` 의 version, 태그는
항상 같은 값이고 워크플로가 셋을 대조해 어긋나면 멈춘다. `npm/data/version.json` 은 투영이라
`python scripts/exportData.py` 를 같은 커밋에서 돌린다. 릴리즈 노트는 GitHub Release 가 커밋 목록에서 만든다.

```powershell
# pyproject.toml 과 npm/package.json 의 version 을 올린 뒤
.venv/Scripts/python.exe -X utf8 -B scripts/exportData.py
.venv/Scripts/python.exe -X utf8 -B -m pytest -q
git add pyproject.toml npm/package.json npm/data/version.json
git commit -F 메시지파일
git tag v0.0.x
git push origin main --tags
```

## 워크플로가 하는 일

1. `ci.yml` 의 게이트 전부 (세 운영체제와 파이썬 조합, ruff, pytest, npm 테스트, 투영 검사, 쓰기 훅 자기 검사).
2. 세 버전 일치 검증. wheel 과 sdist 빌드. 그 wheel 을 격리 venv 에 설치해 Requires 가 비어 있는지, 데이터가
   동봉됐는지, `hanlint README.md` 가 통과하는지 본다.
3. `publish-pypi` (environment `pypi`, OIDC) 와 `publish-npm` (OIDC, npm 11 이상) 이 나란히 올린다.
4. GitHub Release 에 wheel 과 sdist 를 붙인다.

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
