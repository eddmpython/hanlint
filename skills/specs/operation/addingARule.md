---
id: operation.addingARule
title: 규칙을 더하고 고치는 절차
category: operation
purpose: 사람이 하든 AI 가 하든 같은 순서로 규칙을 더하고 고치고 빼게 한다. 순서를 건너뛰면 오탐이 들어온다.
whenToUse:
  - 규칙을 추가하고 싶다
  - 이 지적이 틀렸다
  - 규칙이 시끄럽다
  - 규칙을 빼고 싶다
status: curated
---

# 규칙을 더하고 고치는 절차

## 새 규칙

1. **실측 사례를 먼저 적는다.** 어떤 실제 글의 어떤 문장이 어떤 이유로 나빴는가. 그 문장을 그대로
   가져온다. 사례가 없으면 규칙을 만들지 않는다. 그럴듯한 규칙은 오탐의 다른 이름이다
2. **기계가 결정적으로 잡을 수 있는지 판정한다.** 뜻을 이해해야 잡히면 이 도구의 일이 아니다.
   `start.product` 의 `잡지 않는 것` 에 걸리면 멈춘다
3. **표층으로 되는지, 형태소가 필요한지 정한다.** 표층 정규식으로 충분하면 분석기를 부르지 않는다.
   형태소가 필요하면 먼저 Kiwi 로 그 문장을 찍어 실제 태그열을 본다. 추측으로 태그를 적지 않는다
4. **`rules/<부류>/<규칙이름>.py` 에 파일 하나로 쓴다.** `@rule("이름", mechanism="repeat")` 으로 등록하고
   docstring 에 네 절 (왜, 어디서, 고치기, 안 잡는 것) 과 1번의 실측 사례를 적는다. 기제는 `registry.py` 의
   `MECHANISMS` 다섯 (dictionary, repeat, threshold, contrast, reader) 가운데 하나이고 다섯 밖이면 등록부가 거부한다.
   다섯 밖의
   세는 방법이 정말 필요하면 규칙을 쓰기 전에 멈춰서 운영자에게 묻는다. 기제는 규칙 하나 때문에 늘지 않는다
   (`start.product` 의 규칙은 쌓여도 기제는 다섯이다). 파일이 사는 폴더가 부류의 정본이라
   `hanlint rules` 의 묶음과 `hanlint explain` 의 `같은 부류` 가 거기서 나온다. 임계가 필요하면
   `config/settings.py` 에 기본값을 두고 함수는 거기서 읽는다. 함수 안에 숫자를 박지 않는다
5. **본보기를 쓴다.** `data/exemplars.toml` 에 그 규칙의 `before` 와 `after` 와 `moved` 를 둔다. before 는
   실제로 잡히는 글, after 는 같은 뜻인데 안 잡히는 글, moved 는 손이 한 일 한 마디다. `testExemplars` 가
   둘 다 돌려 확인하므로 규칙을 좁혀 before 가 안 잡히게 되면 빨갛다. 본보기가 없는 규칙은 등록되지 않는다
6. **fixture 를 쓴다.** `tests/fixtures/rules/<규칙이름>.json` 에 `catch` (잡아야 할 문장) 와 `spare` (잡지
   말아야 할 문장) 를 둔다. 실측 사례가 `catch` 의 첫 항목이다. `spare` 에는 그 규칙이 오해하기 쉬운 정상
   문장을 둔다. 두 분석기 모두에 돌아간다
7. **실제 글에 돌려 오탐을 본다.** 규칙이 정상 문장을 짚으면 임계를 올리거나 조건을 좁힌다. 그래도
   안 되면 규칙을 빼고 사례를 `start.product` 의 `잡지 않는 것` 에 남긴다
8. 테스트와 구조 게이트 통과 후 커밋한다

## 사전 항목과 부류별 주의

- **사전 규칙** (cliche, translationese, spelling, spacing, confusable, easyWords): 코드가 아니라 `data/*.toml`
  에 항목을 더한다. 항목마다 pattern, fix, why, source 를 적고 source 에는 국립국어원 조항이나 사전 표제어를
  적는다. `{ㄹ}` `{ㄴ}` 은 그 받침으로 끝나는 음절 부류, `{조사}` 는 낱말 경계다. 뜻에 따라 둘 다 맞는 자리는
  넣지 않는다 (`start.product` 의 잡지 않는 것).
- **code 부류** (inputFileSource, installImport, platformApi): 읽기와 쓰기 함수, 모듈과 패키지 대응, 숨은
  의존성, 플랫폼 API 는 각각 규칙 파일의 정규식과 `data/pythonPackages.txt`, `data/hiddenDeps.txt`,
  `data/platformApis.txt` 가 정본이다.
- 정본 data 를 고쳤으면 `python scripts/exportData.py` 로 npm 투영을 다시 만든다. 규칙을 더하거나 옮기면
  `ruleCategories.json` 도 같이 바뀐다.
- **한 종류의 글에만 안 맞는 규칙은 빼지 말고 프리셋에 넣는다.** 참고 문서에 `noQuestion` 이 도는 것은
  규칙이 틀린 것이 아니라 글의 종류가 다른 것이다. `config/settings.py` 의 `PRESETS` 에 그 규칙 이름을
  더하고 npm 의 같은 표도 같은 작업에서 고친다. `testInitPresetsAgree` 가 두 판을 견준다.
- 겹침 비율 (`hanlint coverage review.json 글.md`) 이 규칙을 더하는 근거다. 못 집은 유형 목록에서 후보를 고른다.

## 오탐 보고가 오면

그 문장을 fixture 의 `spare` 에 먼저 넣는다. 테스트가 실패하는 것을 보고 규칙을 고친다. fixture 없이
규칙만 고치면 다음 사람이 같은 오탐을 다시 만든다.

## 규칙 제거

오탐이 지적의 가치를 넘으면 뺀다. 설정에서 끄는 것과 코드에서 지우는 것은 다르다. 특정 글에서만
소음이면 그 글의 설정에서 끄고, 어디서나 소음이면 코드에서 지우고 이유를 `start.product` 에 남긴다.

## 되돌리기

규칙 파일 하나와 그 테스트를 지우면 된다. 등록부는 파일이 import 되는 순간 채워지므로 따로 지울
목록이 없다.
