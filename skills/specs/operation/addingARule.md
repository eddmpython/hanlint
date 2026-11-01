---
id: operation.addingARule
title: 규칙을 더하고 고치는 절차
category: operation
purpose: 사람이 하든 AI가 하든 같은 순서로 규칙을 더하고 고치고 빼게 한다. 순서를 건너뛰면 오탐이 들어온다.
whenToUse:
  - 규칙을 추가하고 싶다
  - 이 지적이 틀렸다
  - 규칙이 쓸모없는 지적을 많이 낸다
  - 규칙을 빼고 싶다
status: curated
---

# 규칙을 더하고 고치는 절차

## 새 규칙

1. **실측 사례를 먼저 적는다.** 어떤 실제 글의 어떤 문장이 어떤 이유로 나빴는가. 그 문장을 그대로
   가져온다. 사례가 없으면 규칙을 만들지 않는다. 사례 없이 그럴듯하게 만든 규칙은 오탐을 낸다
2. **기계가 늘 같은 기준으로 잡을 수 있는지 판정한다.** 뜻을 이해해야 잡히면 이 도구의 일이 아니다.
   `start.product`의 `잡지 않는 것`에 걸리면 멈춘다
3. **글자 모양으로 가를 수 있는지 정한다.** 정규식과 어절 판정(`analysis/tokenize.py`의 `words`, 조사와 꼬리 사전)으로
   늘 같게 갈리는 것만 규칙이 된다. 그 문장을 넣어 실제 판정을 본 뒤 쓴다. 글자 모양으로 가를 수 없으면 뜻을 읽어야 하므로
   규칙을 만들지 않는다. 형태소 분석기는 없다
4. **`rules/<묶음>/<규칙이름>.py`에 파일 하나로 쓴다.** `@rule("이름", mechanism="repeat")`으로 등록하고
   docstring에 네 절(왜, 어디서, 고치기, 안 잡는 것)과 1번의 실측 사례를 적는다. 찾는 방법은 `registry.py`의
   `MECHANISMS` 다섯(dictionary, repeat, threshold, contrast, reader) 가운데 하나이고 다섯 밖이면 규칙 목록이 거부한다.
   다섯 밖의
   세는 방법이 정말 필요하면 규칙을 쓰기 전에 멈추고 저장소 관리자에게 묻는다. 찾는 방법은 규칙 하나 때문에 늘지 않는다
   (`start.product`의 `규칙이 늘어도 찾는 방법은 다섯이다` 절). 파일이 있는 폴더가 묶음을 정하므로
   `hanlint rules`의 묶음과 `hanlint explain`의 `같은 묶음`이 거기서 나온다. 기준값이 필요하면
   `config/settings.py`에 기본값을 두고 함수는 거기서 읽는다. 함수 안에 숫자를 박지 않는다
5. **예시를 쓴다.** `data/exemplars.toml`에 그 규칙의 `before`와 `after`와 `moved`를 둔다. before는
   실제로 잡히는 글, after는 같은 뜻인데 안 잡히는 글, moved는 고친 사람이 한 일을 한 문장으로 적은 것이다. `testExemplars`가
   둘 다 돌려 확인하므로 규칙을 좁혀 before가 안 잡히게 되면 시험이 실패한다. 예시가 없는 규칙은 등록되지 않는다
6. **fixture를 쓴다.** `tests/fixtures/rules/<규칙이름>.json`에 `catch`(잡아야 할 문장)와 `spare`(잡지
   말아야 할 문장)를 둔다. 실측 사례가 `catch`의 첫 항목이다. `spare`에는 그 규칙이 오해하기 쉬운 정상
   문장을 둔다. fixture는 Python과 npm 두 구현 모두에서 돈다
7. **실제 글에 돌려 오탐을 본다.** 규칙이 정상 문장을 짚으면 기준값을 올리거나 조건을 좁힌다. 그래도
   안 되면 규칙을 빼고 사례를 `start.product`의 `잡지 않는 것`에 남긴다
8. 테스트와 구조 게이트 통과 후 커밋한다

## 사전 항목과 묶음별 주의

- **사전 규칙**(cliche, translationese, spelling, spacing, confusable, easyWords, calqueFrame): 코드가 아니라
  `data/*.toml`에 항목을 더한다. 항목마다 pattern, fix, why, source를 적고 source에는 국립국어원 조항이나 사전
  표제어를 적는다. 같은 문장의 다른 부분(받는 이, 장소, 관용구)이 있으면 정상인 항목은 `unless`에 그 부분의
  정규식을 둔다. 문장 어디에든 맞으면 그 문장에서는 항목이 맞지 않는다. `{ㄹ}`과 `{ㄴ}`은 그 받침으로 끝나는 음절
  묶음, `{조사}`는 단어 경계다. 뜻에 따라 둘 다 맞는 경우는
  넣지 않는다 (`start.product`의 `잡지 않는 것`). 특히 `easyWords`는 다듬은 말 목록에 대체어가 있어도 그 말이
  모든 분야에서 같은 뜻이라는 보증은 아니다. `fix`가 현재 pattern에 걸리는 정상 문맥에서도 대상과 뜻을 지키는지 본다.
  반례가 나오면 pattern을 좁히고 `catch`와 `spare`를 짝지어 검증한다. 글자 모양으로 가를 수 없으면 기본 사전에서 뺀다.
- **code 묶음**(inputFileSource, installImport, platformApi): 읽기와 쓰기 함수, 모듈과 패키지 대응, 숨은
  의존성, 플랫폼 API는 각각 규칙 파일의 정규식과 `data/pythonPackages.txt`, `data/hiddenDeps.txt`,
  `data/platformApis.txt`가 기준이다.
- 기준 자료(`data/`)를 고쳤으면 `python scripts/derive/npmData.py`로 npm 사본을 다시 만든다. 규칙을 더하거나 옮기면
  `ruleCategories.json`도 같이 바뀐다.
- **한 종류의 글에만 안 맞는 규칙은 빼지 말고 프리셋에 넣는다.** 참고 문서에 `noQuestion`이 도는 것은
  규칙이 틀린 것이 아니라 글의 종류가 다른 것이다. `config/settings.py`의 `PRESETS`에 그 규칙 이름을
  더하고 npm의 같은 표도 같은 작업에서 고친다. `testInitPresetsAgree`가 두 구현을 비교한다.
- 겹침 비율(`hanlint coverage review.json 글.md`)이 규칙을 더하는 근거다. 못 짚은 유형 목록에서 후보를 고른다.

## 오탐 보고가 오면

그 문장을 fixture의 `spare`에 먼저 넣는다. 테스트가 실패하는 것을 보고 규칙을 고친다. fixture 없이
규칙만 고치면 다음 사람이 같은 오탐을 다시 만든다.

## 규칙 제거

오탐이 지적의 가치를 넘으면 뺀다. 설정에서 끄는 것과 코드에서 지우는 것은 다르다. 특정 글에서만
쓸모없는 지적만 나오면 그 글의 설정에서 끄고, 어디서나 그렇다면 코드에서 지우고 이유를 `start.product`에 남긴다.

## 되돌리기

규칙 파일 하나와 그 테스트를 지우면 된다. 규칙 목록은 파일을 import할 때 채워지므로 따로 지울
목록이 없다.
