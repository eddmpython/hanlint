import pytest

from hanlint.analysis.grammar import (
    ADJECTIVE,
    CAUSATIVE,
    COPULA,
    HAEYO,
    HANDA,
    HAPNIDA,
    IMPERATIVE,
    PASSIVE,
    PROPOSITIVE,
    VERB,
    convertRegister,
    decomposeVoice,
    documentRegister,
    parsePredicate,
    registerOfWord,
    render,
)


@pytest.mark.parametrize(
    ("source", "handa", "haeyo"),
    [
        ("확인합니다", "확인한다", "확인해요"),
        ("있습니다", "있다", "있어요"),
        ("봅니다", "본다", "봐요"),
        ("엽니다", "연다", "열어요"),
        ("만듭니다", "만든다", "만들어요"),
        ("어렵습니다", "어렵다", "어려워요"),
        ("돕습니다", "돕는다", "도와요"),
        ("듣습니다", "듣는다", "들어요"),
        ("낫습니다", "낫다", "나아요"),
        ("그렇습니다", "그렇다", "그래요"),
        ("다릅니다", "다르다", "달라요"),
        ("보입니다", "보인다", "보여요"),
        ("했습니다", "했다", "했어요"),
        ("하겠습니다", "하겠다", "하겠어요"),
    ],
)
def testCorpusPredicateForms(source, handa, haeyo):
    predicate = parsePredicate(source)
    assert predicate is not None
    assert render(predicate, HAPNIDA) == source
    assert render(predicate, HANDA) == handa
    assert render(predicate, HAEYO) == haeyo


@pytest.mark.parametrize(
    ("source", "hapnida", "haeyo"),
    [
        ("확인한다", "확인합니다", "확인해요"),
        ("연다", "엽니다", "열어요"),
        ("만든다", "만듭니다", "만들어요"),
        ("어렵다", "어렵습니다", "어려워요"),
        ("보인다", "보입니다", "보여요"),
        ("했다", "했습니다", "했어요"),
    ],
)
def testPlainFormsGoBothWays(source, hapnida, haeyo):
    predicate = parsePredicate(source)
    assert predicate is not None
    assert render(predicate, HANDA) == source
    assert render(predicate, HAPNIDA) == hapnida
    assert render(predicate, HAEYO) == haeyo


def testCopulaKeepsExplicitIAndFitsFinal():
    explicit = parsePredicate("예시이다")
    assert explicit is not None and explicit.kind == COPULA
    assert render(explicit, HANDA) == "예시이다"
    assert render(explicit, HAPNIDA) == "예시입니다"
    assert render(explicit, HAEYO) == "예시예요"

    withFinal = parsePredicate("값입니다")
    assert withFinal is not None and withFinal.kind == COPULA
    assert render(withFinal, HANDA) == "값이다"
    assert render(withFinal, HAEYO) == "값이에요"


def testNegativeAuxiliaryInheritsPreviousPredicateKind():
    adjective = parsePredicate("않습니다", "크지")
    verb = parsePredicate("않습니다", "먹지")
    assert adjective is not None and adjective.kind == ADJECTIVE
    assert verb is not None and verb.kind == VERB
    assert render(adjective, HANDA) == "않다"
    assert render(verb, HANDA) == "않는다"


def testQuestionImperativeAndPropositive():
    question = parsePredicate("합니까")
    imperative = parsePredicate("확인하십시오")
    propositive = parsePredicate("찾읍시다")
    assert question is not None and render(question, HANDA) == "하는가"
    assert imperative is not None and imperative.mood == IMPERATIVE
    assert render(imperative, HANDA) == "확인하라"
    assert propositive is not None and propositive.mood == PROPOSITIVE
    assert render(propositive, HANDA) == "찾자"
    assert render(propositive, HAEYO) == "찾아요"
    assert parsePredicate("글자") is None


def testDocumentRegisterUsesDominantDeclarativeStyle():
    assert registerOfWord("확인합니다") == HAPNIDA
    assert registerOfWord("확인한다") == HANDA
    assert registerOfWord("확인해요") == HAEYO
    assert documentRegister(["확인한다", "끝난다", "봅니다"], 0.7) == ("섞임", 2 / 3)
    assert documentRegister(["확인한다", "끝난다", "봅니다"], 0.6) == (HANDA, 2 / 3)


def testRegisterConversionSkipsHeadingsTablesAndFences():
    source = "# 확인합니다\n\n값을 확인합니다.\n\n| 확인합니다 |\n\n```text\n확인합니다.\n```\n"
    converted = convertRegister(source, HANDA)
    assert converted.converted == 1
    assert converted.skipped == 0
    assert converted.text == "# 확인합니다\n\n값을 확인한다.\n\n| 확인합니다 |\n\n```text\n확인합니다.\n```\n"


def testVoiceDecompositionHasPositiveAndNegativePairs():
    passive = decomposeVoice("쓰여지")
    assert passive is not None
    assert (passive.kind, passive.base, passive.markers, passive.reduced) == (
        PASSIVE,
        "쓰이",
        ("접미 피동", "어지"),
        "쓰이",
    )
    causative = decomposeVoice("쉽게 만들었다")
    assert causative is not None
    assert (causative.kind, causative.base, causative.markers, causative.reduced) == (
        CAUSATIVE,
        "쉽",
        ("게", "만들"),
        None,
    )
    assert decomposeVoice("만들어지") is None
    assert decomposeVoice("쉽다") is None
