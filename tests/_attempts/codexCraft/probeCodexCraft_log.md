# codexCraft 실측 기록

작법서 일곱 줄을 읽은 **Codex** 가 더 나은 한국어를 쓰는가.

## 왜 이 실험인가

에이전트는 Claude 와 Codex 둘이다. 작법서를 채택한 craftLift 2회차 (67 대 29, p 0.0001) 는 필자와 심판이 모두
claude-opus-5 였다. 일곱 줄을 뽑은 기계 말뭉치 (`tests/_attempts/aiTells`) 는 어느 모델이 썼는지 기록에 없다.
Codex 에 같은 작법서를 주입하기 전에, 그것이 GPT 필자에게도 이기는지부터 잰다. 판단의 배경은
`memory/evidence/research/decodingIntervention.md` 에 있다.

## 사전 등록 (2026-09-21, 돌리기 전에 적는다)

**갈래 둘.** 같은 과제, 같은 필자, 과제마다 새 세션.

| 갈래 | 무엇을 주나 |
|---|---|
| `plain` | 과제만 준다 |
| `craft` | 작법서 본문을 먼저 읽히고 과제를 준다 |

작법서는 제품이 싣는 본문 `src/hanlint/data/koreanProse.txt` (1,249자) 다. craftLift 가 잰 판 (커밋 35fa30f 의
craftGuide.md, 1,218자) 과 일곱 줄의 문장이 같고, 명령형 뒤 마침표와 첫머리 한 문장만 다르다. 주입 경로 (훅) 가
아니라 과제 앞에 붙이는 craftLift 의 방식을 그대로 써서, 바뀌는 것을 필자 모델 하나로 둔다.

**프롬프트.** `probeCodexCraft.py prompt <갈래> <과제>` 가 그대로 찍는다. plain 은 아래 두 문단이고, craft 는
작법서 본문과 `---` 줄을 그 앞에 붙인다.

```text
도구를 쓰지 않는다. 파일을 읽거나 명령을 실행하지 않고 바로 답한다.

주제: {주제}

이 주제로 한국어 산문 한 편을 500자 안팎으로 쓴다. 제목 없이 본문만 낸다.
```

첫 줄은 전역 AGENTS.md 가 파일을 먼저 읽으라고 하기 때문에 넣었다. 두 갈래에 똑같이 붙는다.

**과제.** `tasks.json` 의 96개. 네 영역 (생활과 건강, 일과 돈, 기술과 과학, 사회와 문화) 에서 24개씩이다.
craftLift 의 과제 목록은 남아 있지 않아 겹침을 대조할 수 없다. 기억나는 주제 (습도와 결로, 가구 배치, 도마,
달리기와 무릎) 는 피했다.

**필자.** 이 기계의 Codex 설정 그대로다 (`meta.json` 이 판과 모델과 추론 강도를 적는다). 사용자의 전역
AGENTS.md, 스킬, 훅도 그대로 돈다. 두 갈래에 같으므로 차이를 만들지 않고, 에이전트가 실제로 쓰는 환경을 잰다.

**심판.** 주 심판은 fresh-context claude-opus-5 다. craftLift 의 `judge` 가 만든 묶음을 그대로 받는다. 작법서도
규칙 이름도 받지 않고 A/B 차례는 과제마다 씨앗으로 섞인다. 필자와 가족이 달라 같은 가족 편향이 줄어든다.
보조 심판은 같은 묶음을 받은 Codex 다. 보조 심판은 판정을 바꾸지 않고 주 심판과의 일치율만 적는다.

**판정 조건.** craftLift 와 같다.

- **채택.** craft 가 plain 을 이긴다. 부호검정 p < 0.01 이고 승률 차 +10%p 이상. Codex 에도 작법서 주입을 켠다.
- **폐기.** craft 가 진다. p < 0.01 이고 승률 차 -10%p 이하. Codex 에는 주입하지 않고 GPT 에 해롭다고 적는다.
- **무효.** craft 쪽에서 표지가 안 줄었다 (`follow` 의 기준). 지침을 안 따른 것이라 선호를 해석하지 않는다.
- 위 어디에도 안 걸리면 **효과 없음**. Codex 에는 주입하지 않는다.

**부 지표.**

- `follow` 의 여섯 표지 비율과 긴 문장 비율. plain 쪽 수를 craftLift 2회차의 Claude plain 과 사람 네 장르 띠에
  나란히 적는다. GPT 가 쓴 한국어의 버릇이 Claude 와 같은지 보는 자리다.
- plain 96편에 `aiTells/probeContrast.py` 를 걸어 GPT 쪽에만 도드라지는 꼴을 캔다. 표본이 작아 가설만 낸다.
  규칙 후보가 되려면 따로 표본을 늘려 잰다.

**미리 적는 함정.**

- 1번 줄 (긴 문장) 이 Claude 에서 두 번 진 자리였다. GPT 에서도 같은 이유의 패배가 나오는지 심판의 이유를 본다.
- 필자 세션마다 cinch 훅이 돈다. 훅이 글에 영향을 주면 두 갈래에 같게 준다.
- 첫 호출 몇 개는 시범이다. 시범 글은 본 시험 폴더에 넣지 않는다.

**쓴 글의 자리.** `~/.cache/hanlint/attempts/codexCraft/` 다. craftLift 는 쓴 글을 남기지 않아 다시 판정할 수
없었다. 이번 글은 사람 블라인드 평가에 다시 쓰므로 남긴다.

## 1회차 결과 (2026-09-21). **채택**

필자는 codex-cli 0.155.1, 모델 gpt-5.6-sol, 추론 강도 xhigh 다 (`meta.json`). 과제 96개, 갈래 둘, 192편을
실패 없이 썼다. 과제마다 새 세션이다.

### 지침 준수 (부 지표). 따랐다

```text
표지 (천문장당)         plain    craft
이유가 여기             0.00     0.00
그다음                 0.00     0.00
n 번째는               0.00     0.00
편이 낫/좋             18.45     0.00
셈이다                 3.69     0.00
X가 아니라 Y다          62.73     9.27

긴 문장 비율            0.0%     4.9%    사람 최소 4.6%
길이 평균 (어절)        11.88    13.80
길이 고름               0.33     0.52
```

### 블라인드 선호 (주 지표)

```text
주 심판 (fresh-context claude-opus-5, 묶음 넷)
심판 96건: craft 90, plain 6, same 0
승률 craft 93.8% 대 plain 6.2% (차 +87.5%p)
부호검정 p 0.0000

보조 심판 (Codex, 같은 묶음)
심판 96건: craft 77, plain 19, same 0
승률 craft 80.2% 대 plain 19.8% (차 +60.4%p)
```

사전 등록한 채택 조건 (p < 0.01, 차 +10%p 이상) 을 넘었다. 두 심판의 판정은 96건 가운데 75건 (78.1%) 이
같다. A 자리를 고른 비율은 주 심판 50.0%, 보조 심판 46.9% 이고 craft 가 A 자리에 온 과제는 50개라 자리
쏠림은 없다. 판정대로 **Codex 에도 작법서 주입을 켠다.**

### 진 6건이 모두 1번 줄에서 졌다

주 심판이 plain 을 고른 6건의 이유가 전부 긴 문장이다.

```text
h03 B는 내용이 정확하지만 한 문장이 지나치게 길게 이어져 읽기가 무너지고
h09 A는 ... 무관한 내용을 한 문장에 몰아넣었고
h11 A는 한 문장이 과도하게 길고
t24 A는 앞부분 문장이 너무 많은 내용을 떠안아 읽기가 무겁다
w02 B는 첫 문장이 길고 끝의 확인 목록이 무겁다
w05 A는 반대 의견을 다루는 한 문장이 지나치게 길고
```

craftLift 1, 2회차에서 Claude 필자가 진 이유와 같다. 필자 가족이 바뀌어도 1번 줄 (긴 문장을 두어라) 하나만
글을 망친다. 이 수를 보고 1번 줄을 고치지 않는다. craftLift 3회차에서 1번 줄에 세 줄을 더한 판은 55 대 41
(p 0.1843) 로 미달이었다. 1번 줄을 **지운** 판은 아직 잰 적이 없으므로, 따로 사전 등록해 내보낸 판과 견준다.

### GPT 가 쓴 한국어의 버릇

plain 쪽 수를 craftLift 2회차의 Claude plain 과 나란히 둔다 (천문장당).

| 표지 | GPT plain | Claude plain | 사람 최대 |
|---|---|---|---|
| 이유가 여기 | 0.00 | 1.69 | 0.01 |
| 그다음 | 0.00 | 5.08 | 0.06 |
| n 번째는 | 0.00 | 1.69 | 0.22 |
| 편이 낫/좋 | 18.45 | 10.15 | 0.47 |
| 셈이다 | 3.69 | 6.77 | 0.13 |
| X가 아니라 Y다 | 62.73 | 69.37 | 7.05 |
| 긴 문장 비율 | 0.0% | 0.0% | 4.6~15.5% |

두 가족이 헤지, 부정 병렬, 긴 문장 없음을 함께 가진다. 설명 가리키기와 산문 번호는 GPT 에 없다. 작법서가 GPT
에서도 이긴 것은 공통인 셋이 무겁기 때문으로 보인다.

`aiTells/probeContrast.py --min-ai 5` 로 plain 96편을 사람 네 장르와 견줬다. 문서 5편 이상에 나오고 사람
최대 비율보다 20배 넘는 꼴은 대부분 권고의 헤지였다. `편이 좋다` (16%, 사람 0.1% 이하), `살펴야 한다` (14%),
`것이 좋다` (11%), `필요는 없다` (10%), `일이 아니라` (14%). `잠들기`, `서랍`, `골목` 같은 주제어도 섞였다.
표본이 96편이라 가설로만 적는다. 규칙 후보가 되려면 GPT 글을 늘려 aiTells 2회차의 방식으로 다시 잰다.

### 재현

```console
python -X utf8 -B tests/_attempts/codexCraft/probeCodexCraft.py write ~/.cache/hanlint/attempts/codexCraft/round1
python -X utf8 -B tests/_attempts/craftLift/probeCraftLift.py follow ~/.cache/hanlint/attempts/codexCraft/round1
python -X utf8 -B tests/_attempts/craftLift/probeCraftLift.py judge <시험 폴더> --output-dir <시험 폴더>/judge --batch 24
python -X utf8 -B tests/_attempts/codexCraft/probeCodexCraft.py gptJudge <시험 폴더>/judge --output-dir <시험 폴더>/gptJudgments
python -X utf8 -B tests/_attempts/craftLift/probeCraftLift.py score <시험 폴더> --judgments <시험 폴더>/claudeJudgments \
    --orders <시험 폴더>/judge/order.json
```

주 심판은 묶음 파일 하나씩을 받은 fresh-context 에이전트 넷이다. 받은 지시는 "그 파일을 읽고 그 지시를 그대로
따르고 JSON 배열만 낸다" 뿐이다. 답은 `claudeJudgments/judge-0N.json` 에 그대로 두었다.
