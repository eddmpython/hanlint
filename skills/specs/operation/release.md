---
id: operation.release
title: 배포
category: operation
purpose: PyPI 에 올리는 절차와 그 전에 확인할 것. 릴리즈는 명시 지시가 있을 때만 한다.
whenToUse:
  - 배포하고 싶다
  - 버전을 올리나
  - PyPI 에 어떻게 올리나
  - 깨끗한 환경에서 설치가 되나
verify:
  - .venv/Scripts/python.exe -X utf8 -B -m pip install --quiet build twine
status: curated
---

# 배포

`0.0.x` 라인에서 명시 지시가 있을 때만 릴리즈한다. 일상 커밋은 버전과 태그를 건드리지 않는다.

## 전에 확인

1. `operation.verify` 의 셋이 green.
2. 깨끗한 환경에서 의존성 0 으로 설치되는지. 공통 실행 공간에 임시 venv 를 만들어 본다.

```powershell
python -X utf8 -B -m venv C:/Users/MSI/AppData/Local/dev-workspace/hanlintInstall
C:/Users/MSI/AppData/Local/dev-workspace/hanlintInstall/Scripts/python.exe -X utf8 -B -m pip install --quiet .
C:/Users/MSI/AppData/Local/dev-workspace/hanlintInstall/Scripts/hanlint --version
C:/Users/MSI/AppData/Local/dev-workspace/hanlintInstall/Scripts/hanlint README.md
```

`pip show hanlint` 의 Requires 가 비어 있어야 한다. 끝나면 그 venv 를 지운다.

## 릴리즈 커밋

버전 +1 과 태그 `v0.0.x` 를 같은 커밋에. `pyproject.toml` 의 version 과 태그는 항상 같은 값이다.
릴리즈 노트는 릴리즈 커밋 메시지다.

```powershell
git commit -F 메시지파일
git tag v0.0.x
git push origin main --tags
```

## PyPI

```powershell
.venv/Scripts/python.exe -X utf8 -B -m build --outdir ../hanlint.out/dist
.venv/Scripts/python.exe -X utf8 -B -m twine upload ../hanlint.out/dist/*
```

토큰은 운영자가 가진다. 저장소와 로그에 남기지 않는다. 올린 뒤 `pip install hanlint==0.0.x` 로 새 venv 에서
받아 `hanlint --version` 을 확인한다.

## 되돌리기

PyPI 는 같은 버전을 다시 올릴 수 없다. 잘못 올렸으면 그 버전을 yank 하고 다음 버전으로 고친다.
