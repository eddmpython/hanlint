---
id: operation.webEditor
title: 브라우저 편집기
category: operation
purpose: 같은 npm 엔진을 브라우저 편집과 개인 기록, GitHub Pages 배포에 연결하는 경계.
whenToUse:
  - 브라우저 편집기를 바꾼다
  - 개인 GitHub 저장과 Pages 배포를 확인한다
status: observed
---

# 브라우저 편집기

`web`은 첫 화면의 편집, 지적과 문체 본보기, 원문 보호, 수정본과 승인 고침을 소유한다. 엔진은
`npm/src/index.js`의 공개 API다. 브라우저가 따로 만든 규칙은 없다. 사전은 같은 npm 투영을 배포할 때
묶고, 계약 해시는 Node와 브라우저의 UTF-8 결과를 대조한다. 파일 경로 API는 Node에서만 실행한다.

일반 원고의 보호 비교는 `compareRevision`이 기존 표면 검사와 제목 비교를 호출한다. 빈 글이나 반복
제목도 관찰할 수 있어야 하므로 승인 계약을 자동 생성하지 않는다. 승인 패치는 원문 전체를 담은
기존 v1 계약으로 검증하고 H2 순서 변화도 거부한다. 명시한 계약의 입력 제약은 그대로 적용한다.

사용자의 저장과 기여 절차는 [사용과 저장 안내](https://eddmpython.github.io/hanlint/guide.html)가 소유한다. 기록 형식과 한도는
`web/records.js`, 토큰 수명과 원격 파일 갱신은 `web/github.js`가 소유한다. 수정 이력을 승인 패치로
자동 변환하지 않는다. 사례를 내려받는 행동도 외부 제출이나 공통 규칙의 승인이 아니다.

## 배포

첫 화면은 히어로 하나, 왼쪽 원문과 오른쪽 결과, 그 아래 수정본 입력으로 구성한다. 원문을 넣으면
바로 검사하고 수정 중에는 수정본을 검사한다. 수정본을 전체 교체해도 원문을 바꾸지 않는다. 원문은
수정 중 읽기 전용이며 새 원고를 열 때 기존 작업을 기록한다. 같은 문장의 지적은 묶어서 이유와
본보기를 바로 보여 준다. 아래 수정본은 원문을 미리 담아 별도 시작 버튼 없이 편집한다.
보호 조건과 승인 후보는 수정 후 나타나고 기록과 보관 버튼은 항상 보인다. 기록 메모와 수정 방식은
화면에서 입력하고 한 번 눌러 저장한다. 전후 문장이 보이는 기억 버튼에서 뜻 유지와 재사용을 승인한다.
기존 개인 기록 형식은 그대로 읽으며 외부 쓰기와 삭제 확인은 유지한다.

`scripts/derive/site.py --output <빈 출력 폴더>`가 정적 배포물을 조립한다. 원본을 고쳐서 빌드하고 기존
출력에 덧씌우지 않는다. 로컬 산출물은 전역 development-hygiene의 공통 실행 공간에 둔다.
`.github/workflows/pages.yml`이 기존 CI를 먼저 실행하고 배포한다. 프로젝트 경로는 상대 경로라
Fork에서도 Pages 설정을 활성화하면 같은 소스를 제공한다. 사이트 소스에 개인 원고나 토큰을 넣지 않는다.

Pages는 `main`의 검증된 소스를 제공한다. npm과 PyPI는 별도 릴리즈이므로 사이트에 들어간 API가 아직
설치 패키지에는 없을 수 있다. 공개 상태는 `CHANGELOG.md`의 Unreleased와 배포 버전으로 구분한다.

## 로컬 실행

저장소 루트에서 Python 3.11 이상으로 조립한다. 다음 PowerShell 예시의 작업 폴더 이름은 실행마다
새로 고른다. 출력 폴더에 파일이 이미 있으면 빌드는 덮어쓰지 않고 멈춘다.

```powershell
uv sync
$sitePath = Join-Path $env:LOCALAPPDATA 'dev-workspace/hanlintPreview/site'
uv run --no-sync python -X utf8 -B scripts/derive/site.py --output "$sitePath"
uv run --no-sync python -X utf8 -B -m http.server 4179 --bind 127.0.0.1 --directory "$sitePath"
```

`http://127.0.0.1:4179/`를 연다. 파일을 직접 여는 `file://` 주소는 모듈과 Worker 실행에 맞지 않는다.
화면을 바꾼 뒤에는 서버를 멈추고 새 출력 폴더에 조립한다. 검수가 끝나면 서버와 자신이 만든 출력만 정리한다.
Linux와 macOS에서는 같은 빌드와 서버 명령에 저장소 밖 출력 경로를 넘긴다.

## 화면을 바꿀 때

| 바꿀 내용 | 소유 파일 |
|---|---|
| 첫 화면 구조와 안내 문구 | `web/index.html` |
| 색, 간격과 반응형 배치 | `web/style.css` |
| 시스템 테마, 선택과 복원 | `web/theme.js` |
| 심볼과 파비콘 | `web/brand.png` |
| 글꼴과 배포 고지 | `web/pretendard.woff2`, `web/pretendard.LICENSE.txt` |
| 제작자 채널 | `web/channels.js` |
| 사용자 안내 | `web/guide.html` |
| 자료 고지 페이지 | `scripts/derive/site.py`와 `npm`의 라이선스·출처 고지 |

첫 화면은 예문과 실제 지적을 바로 보여 준다. 소개를 읽거나 가입해야 편집할 수 있는 흐름을 넣지 않는다.
브랜드와 채널을 바꿀 때는 편집기와 안내의 링크를 함께 확인한다. 라이선스와 자료 출처 고지는 유지한다.

글꼴은 [Pretendard 1.3.9](https://github.com/orioncactus/pretendard/tree/v1.3.9)의 가변 WOFF2 원본이다.
사이트에서 직접 제공하고 SIL OFL 고지를 배포물에 포함한다. 글을 입력할 때 외부 글꼴 서버에 요청하지 않는다.

다크·라이트 색 쌍은 CSS의 `light-dark()`로 관리한다. 시스템 선호를 기본으로 삼고 선택한 테마는
사이트 경로별 별도 키에 저장한다. 원고 기록과 분리하며 안내·라이선스도 같은 테마를 적용한다.

## 검증

`npm/test/browserCore.test.js`와 `tests/gates/testWebLearn.py`가 해시, 문장 대응과 수정 후보를 대조한다.
`npm/test/engineClient.test.js`는 검사 준비 전 요청 유실과 실패를, `npm/test/webRecords.test.js`는
기록의 왕복, 인증 정보 제외, GitHub의 최초 생성과 갱신 및 충돌을 확인한다.
`tests/gates/testWebBuild.py`는 코어와 자료의 누락, 저장소 내부 출력과 기존 파일 덮어쓰기를 검사한다.

명령줄 밖 화면은 설치된 정확 버전의 pyproc로 확인한다. 공통 실행 공간에 localhost만 허용한
제어 프로파일을 만들고 `node scripts/measure/site.mjs <manifest> <출력 폴더> [URL]`을 실행한다.
데스크톱과 모바일에서 두 테마, 지적의 즉시 표시, 한 번 수정·기록·기억, 되돌리기, 기록 복원, 입력 비실행과 엔진 동등성을
확인하고 스크린샷을 눈으로 본다. 사용한 target, session과 artifact를 마지막에 닫는다.

WebMCP를 지원하는 브라우저에는 같은 편집 동작을 등록한다. 지원하지 않는 브라우저의 화면 기능은
영향을 받지 않는다. 토큰 입력과 외부 저장은 구조화 도구로 노출하지 않는다.
