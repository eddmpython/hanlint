# craftLineOne 실측 기록

작법서에서 1번 줄 (긴 문장을 두어라) 을 지운 판이 내보낸 판보다 나은 한국어를 쓰게 하는가.

## 왜 이 실험인가

작법서 쪽이 진 이유가 세 회차 모두 1번 줄이었다. craftLift 1, 2회차 (필자 claude-opus-5) 에서 진 17건과 29건의
이유가 긴 문장에 몰렸고, codexCraft (필자 Codex) 에서 진 6건은 전부 긴 문장이다. craftLift 3회차는 1번 줄에 세
줄을 더한 판을 쟀고 55 대 41 (p 0.1843) 로 미달이었다. 1번 줄을 **지운** 판은 잰 적이 없다.

1번 줄의 근거도 약해졌다. 커밋 56d59a4 가 글 단위로 찍어 보니 사람 글 4,021편의 30.2% 에 긴 문장이 하나도
없었다. 집계 배수 (15~23배) 는 기계 글이 짧아서 생긴 것이었다.

## 사전 등록 (2026-09-22, 돌리기 전에 적는다)

**갈래 둘.** 두 갈래 모두 작법서를 먼저 읽히고 과제를 준다. 다른 것은 작법서 본문뿐이다.

| 갈래 | 작법서 |
|---|---|
| `shipped` | 제품이 싣는 `src/hanlint/data/koreanProse.txt` (1,249자) |
| `noLong` | `noLongLine.txt` (1,038자). 1번 절을 지우고, 번호를 하나씩 당기고, 제목의 `일곱` 을 `여섯` 으로, 마지막 줄의 `앞의 여섯` 과 `1번부터 6번까지` 를 `앞의 다섯` 과 `1번부터 5번까지` 로 바꿨다. 그 밖의 글자는 같다 |

**프롬프트.** `probeLineOne.py prompt <갈래> <과제>` 가 그대로 찍는다. 작법서 본문, `---` 줄, 그리고 codexCraft 와
같은 두 문단이다 (`도구를 쓰지 않는다...`, `주제: ...`, `이 주제로 한국어 산문 한 편을 500자 안팎으로 쓴다...`).

**과제.** `tasks.json` 의 새 96개. 네 영역에서 24개씩이고 codexCraft 의 96개와 겹치지 않는다. 두 필자가 같은
과제를 쓴다.

**필자 둘.** 과제마다 새 세션이다.

- Codex: `codex exec --ephemeral --disable hooks`. 모델과 추론 강도는 이 기계의 설정 그대로다.
- Claude: `claude -p --setting-sources project,local --model opus --effort xhigh`. 사용자 설정을 빼야 훅이 빠지므로
  모델과 강도는 사용자 설정 (opus, xhigh) 과 같은 값을 명시한다. 이 조건에서 "작법서가 문맥에 있느냐" 물으면
  NONE 이라고 답하는 것을 시범에서 확인했다.

훅을 끄는 까닭. 2026-09-21 부터 이 기계의 전역 훅이 세션마다 내보낸 판을 싣는다. 켜 두면 noLong 갈래도 1번 줄을
본다. 필자 세션마다 `meta.json` 이 판, 모델, 강도, 두 작법서의 해시를 적는다.

**심판.** 주 심판은 fresh-context claude-opus-5 다. craftLift 의 `judge --arms shipped,noLong` 이 필자마다 만든
24과제 묶음 넷을 하나씩 받는다. 작법서도 갈래 이름도 받지 않고 A/B 차례는 과제마다 씨앗으로 섞인다. 보조 심판은
같은 묶음을 받은 Codex (훅 끔) 이고 판정을 바꾸지 않는다.

**판정 조건.**

- **교체.** 두 필자를 합친 192쌍에서 noLong 이 이기고 부호검정 p < 0.01, 승률 차 +10%p 이상이며, 필자마다의
  승률 차가 둘 다 0 이상이다. 그러면 제품의 작법서에서 1번 줄을 지운다.
- **1번 줄이 득.** 합친 192쌍에서 shipped 가 이기고 p < 0.01, 승률 차 -10%p 이하. 1번 줄을 남기고 그렇게 적는다.
- 그 밖은 **유지**. 바꿀 근거가 모자라면 안 바꾼다 (craftLift 3회차와 같은 원칙).

192쌍을 합치는 까닭. 참 승률이 60% 라면 96쌍의 기대값은 58 대 38 이고 p 는 0.05 언저리라 판정력이 모자란다.
192쌍이면 115 대 77 이고 p 는 0.007 언저리다. 한 가족에서만 이기는 판을 두 가족에 싣지 않으려고 필자마다의
방향 조건을 더한다.

**부 지표.** `follow` 가 필자와 갈래마다 다섯 표지 비율, 긴 문장 비율, 길이 평균과 고름을 낸다. noLong 에서
긴 문장이 줄 것으로 본다. 표지는 두 갈래 모두 작법서를 읽으므로 둘 다 낮아야 한다. 선호의 해석을 바꾸지 않는다.

**미리 적는 함정.**

- Claude 필자 쪽은 심판과 필자가 같은 가족이다 (craftLift 와 같다). Codex 필자 쪽이 그 편향의 대조가 된다.
- noLong 이 짧아서 이길 수 있다. 심판에게 길이로 고르지 말라는 지시가 묶음 머리에 있다. 길이 평균을 함께 적는다.
- 시범 한 과제 (h01) 는 본 시험 폴더 밖에서 썼고 본 시험에 넣지 않는다.

**쓴 글의 자리.** `~/.cache/hanlint/attempts/craftLineOne/` 에 필자마다 남긴다.

## 결과 (2026-09-22). **유지**

두 필자 모두 과제 96개 192편을 실패 없이 썼다. 필자 조건은 `meta.json` 이 적는다 (Codex 0.155.1, gpt-5.6-sol,
xhigh, 훅 끔. Claude Code 2.1.278, opus, xhigh, 사용자 설정 뺌).

### 부 지표

```text
                  Codex 필자            Claude 필자
                  shipped   noLong      shipped   noLong
X가 아니라 Y다       5.50      4.14         1.00      0.00
편이 낫/좋           0.00      0.00         1.00      0.00
그 밖 네 표지        0.00      0.00         0.00      0.00
긴 문장 비율         2.5%      0.0%         7.5%      0.0%
길이 평균 (어절)    13.50      9.99        12.37      8.87
길이 고름            0.48      0.34         0.69      0.41
공백 뺀 글자 평균     380       376          385       388
```

1번 줄을 지우면 두 가족 모두 긴 문장이 0% 로 떨어지고 문장이 짧고 고르게 된다. 글 전체 길이는 두 갈래가 같다.
다른 표지는 두 갈래 모두 거의 0 이라 작법서의 나머지 줄은 둘 다 지켰다.

### 블라인드 선호

```text
주 심판 (fresh-context claude-opus-5)
codex:  noLong 39, shipped 57 (차 -18.8%p, p 0.0822)
claude: noLong 73, shipped 23 (차 +52.1%p, p 0.0000)
합침:   noLong 112, shipped 80 (차 +16.7%p, p 0.0250)

보조 심판 (Codex, 훅 끔)
codex:  noLong 34, shipped 62 (차 -29.2%p, p 0.0056)
claude: noLong 49, shipped 47 (차 +2.1%p, p 0.9188)
```

사전 등록한 교체 조건에 못 미친다. 합친 p 가 0.0250 이라 0.01 을 넘고, Codex 필자의 승률 차가 음수다. 판정은
**유지** 다. 제품의 작법서를 바꾸지 않는다. `1번 줄이 득` 조건 (합쳐서 shipped 가 p < 0.01 로 이김) 에도 걸리지
않는다. A 자리 선택은 주 심판 43/96 와 45/96, 보조 심판 46/96 와 49/96 이고 noLong 이 A 자리에 온 과제는 필자마다
50개라 자리 쏠림은 없다. 두 심판의 일치는 Codex 필자 69/96, Claude 필자 62/96 이다.

### 읽은 것: 1번 줄의 효과는 필자 가족을 탄다

**Codex 필자에게 1번 줄은 득이다.** 두 심판이 같은 방향이다 (57 대 39, 62 대 34). 주 심판이 shipped 를 고른
57건 가운데 12건의 이유가 noLong 글이 "짧게 끊긴다", "나열한다" 였다. noLong 이 이긴 39건 가운데 13건의 이유는
shipped 의 긴 문장이었다. 1번 줄이 없으면 GPT 는 고른 단문 나열로 돌아간다 (길이 고름 0.34. codexCraft 의 GPT
plain 이 0.33 이었다).

**Claude 필자에게는 심판이 갈린다.** Claude 심판은 73 대 23 으로 noLong 을 골랐고 이유 96건 가운데 38건이 긴
문장이다. Codex 심판은 49 대 47 로 차이를 못 봤다. 같은 가족 심판만 보는 차이라 증거가 한쪽뿐이다.

앞 기록의 "필자 가족이 바뀌어도 1번 줄 하나만 글을 망친다" (codexCraft) 는 틀린 읽기였다. 그것은 작법서 대
과제만 (plain) 에서 **진 자리의 이유** 를 모은 것이고, 1번 줄을 빼면 이긴 자리에서 무엇을 잃는지는 보지 않았다.
진 이유만 모으면 그 줄의 비용만 보이고 이득은 안 보인다.

### 다음 물음

- Claude 필자의 noLong 대 shipped 는 두 심판이 갈리는 자리라 사람 블라인드가 가장 값진 곳이다. 이 폴더의 Claude
  필자 글 96쌍에서 30쌍을 뽑아 사람이 판정하면 Claude 심판과 Codex 심판 가운데 누가 사람과 맞는지 갈린다.
- 에이전트마다 다른 작법서를 싣는 안 (Claude 에 noLong, Codex 에 shipped) 은 이번 수를 보고 세운 가설이다.
  사람 판정이 Claude 심판 쪽이면 그때 따로 사전 등록해 잰다.

### 재현

```console
python -X utf8 -B tests/_attempts/craftLineOne/probeLineOne.py write ~/.cache/hanlint/attempts/craftLineOne --writer codex
python -X utf8 -B tests/_attempts/craftLineOne/probeLineOne.py write ~/.cache/hanlint/attempts/craftLineOne --writer claude
python -X utf8 -B tests/_attempts/craftLineOne/probeLineOne.py follow ~/.cache/hanlint/attempts/craftLineOne
python -X utf8 -B tests/_attempts/craftLift/probeCraftLift.py judge <폴더>/<필자> --output-dir <폴더>/<필자>/judge --batch 24 \
    --arms shipped,noLong
python -X utf8 -B tests/_attempts/craftLineOne/probeLineOne.py gptJudge <폴더>/<필자>/judge --output-dir <폴더>/<필자>/gptJudgments
python -X utf8 -B tests/_attempts/craftLineOne/probeLineOne.py score <폴더> --judgments claudeJudgments
```

주 심판은 필자마다 묶음 파일 하나씩을 받은 fresh-context 에이전트 넷이고, 받은 지시는 "그 파일을 읽고 그 지시를
그대로 따르고 JSON 배열만 낸다" 뿐이다. 답은 `<필자>/claudeJudgments/judge-0N.json` 에 그대로 두었다.

## 사람 판정 사전 등록 (2026-09-22, 판정 전에 적는다)

**물음.** Claude 필자의 noLong 대 shipped 에서 두 심판이 갈렸다 (Claude 심판 73 대 23, Codex 심판 49 대 47). 사람은
어느 심판과 맞는가.

**표본 30쌍.** Claude 필자 96쌍 가운데 두 심판이 갈린 34쌍에서 24쌍, 같았던 62쌍에서 6쌍을 씨앗 20260922 로
뽑는다 (`probeLineOne.py humanSheet`). 갈린 쌍에서 사람이 A나 B를 고르면 그 선택은 정확히 한 심판과 맞는다.
같았던 6쌍은 사람이 두 심판과 함께 가는지 보는 대조다.

**보이는 것.** 주제와 두 글뿐이다. A/B 차례는 새 씨앗으로 섞고, 작법서, 갈래 이름, 심판 판정은 보이지 않는다.
짝과 갈래의 대응 (`key.json`) 은 판정지 밖에 둔다. 지시는 AI 심판과 같다. 더 나은 한국어 산문 하나를 고르고,
내용의 정확함이 비슷하면 읽기와 글의 힘으로 고르며, 사실상 같으면 비슷하다를 고른다.

**판정.**

- 갈린 24쌍에서 사람이 한 심판과 맞은 수를 다른 심판과 맞은 수와 부호검정으로 견준다 (비슷하다는 뺀다).
  p < 0.05 면 그 심판이 이 물음에서 사람의 대리가 된다. 24쌍이 다 결정되면 18 대 6 이 그 선이다.
- Claude 심판 쪽이면, 에이전트마다 다른 작법서를 싣는 안 (Claude 에 noLong) 을 따로 사전 등록해 잰다.
- Codex 심판 쪽이면, 같은 가족 심판이 긴 문장을 과하게 벌한다고 적고 앞으로 작법 실측의 주 심판을 필자와 다른
  가족으로 둔다. 작법서는 그대로다.
- 어느 쪽도 아니면 결론 없음으로 적는다.
- 30쌍 전체에서 사람이 고른 noLong 대 shipped 도 적되 표본을 갈린 쌍으로 기울였으므로 전체 선호의 추정으로
  쓰지 않는다.

**판정지.** `probeLineOne.py humanSheet` 가 `~/.cache/hanlint/attempts/craftLineOne/human/` 에 판정지와 풀이표
(`key.json`) 를 쓴다. 판정지는 claude.ai 아티팩트로 발행했고 (https://claude.ai/artifact/491AGwscHTEoeVhh91MmUb,
비공개) 고른 판정을 그 아티팩트의 `verdicts` 모음에 쌍마다 문서 하나로 저장한다. 채점은 그 모음을
`{짝: {choice}}` JSON 으로 옮긴 뒤 `probeLineOne.py humanScore <시험 폴더> --key <key.json> --verdicts <그 JSON>` 이다.
