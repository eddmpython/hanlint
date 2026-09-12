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

사용자의 저장과 기여 절차는 [저장과 데이터 안내](../../../web/guide.html)가 소유한다. 기록 형식과 한도는
`web/records.js`, 토큰 수명과 원격 파일 갱신은 `web/github.js`가 소유한다. 수정 이력을 승인 패치로
자동 변환하지 않는다. 사례를 내려받는 행동도 외부 제출이나 공통 규칙의 승인이 아니다.

## 배포

`scripts/derive/site.py --output <빈 출력 폴더>`가 정적 배포물을 조립한다. 원본을 고쳐서 빌드하고 기존
출력에 덧씌우지 않는다. 로컬 산출물은 전역 development-hygiene의 공통 실행 공간에 둔다.
`.github/workflows/pages.yml`이 기존 CI를 먼저 실행하고 배포한다. 프로젝트 경로는 상대 경로라
Fork에서도 Pages 설정을 활성화하면 같은 소스를 제공한다. 사이트 소스에 개인 원고나 토큰을 넣지 않는다.

## 검증

`npm/test/browserCore.test.js`와 `tests/gates/testWebLearn.py`가 해시, 문장 대응과 수정 후보를 대조한다.
`npm/test/engineClient.test.js`는 검사 준비 전 요청 유실과 실패를, `npm/test/webRecords.test.js`는
기록의 왕복, 인증 정보 제외, GitHub의 최초 생성과 갱신 및 충돌을 확인한다.
`tests/gates/testWebBuild.py`는 코어와 자료의 누락, 저장소 내부 출력과 기존 파일 덮어쓰기를 검사한다.

명령줄 밖 화면은 설치된 정확 버전의 pyproc로 확인한다. 공통 실행 공간에 localhost만 허용한
제어 프로파일을 만들고 `node scripts/measure/site.mjs <manifest> <출력 폴더> [URL]`을 실행한다.
데스크톱과 모바일에서 첫 지적 표시, 실제 버튼 수정과 되돌리기, 기록 복원, 입력 비실행과 엔진 동등성을
확인하고 스크린샷을 눈으로 본다. 사용한 target, session과 artifact를 마지막에 닫는다.

WebMCP를 지원하는 브라우저에는 같은 편집 동작을 등록한다. 지원하지 않는 브라우저의 화면 기능은
영향을 받지 않는다. 토큰 입력과 외부 저장은 구조화 도구로 노출하지 않는다.
