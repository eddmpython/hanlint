from scripts.fetchLearningVocabulary import parseSource, render


def testParserKeepsOriginalWordAndProjectsLexeme(monkeypatch):
    monkeypatch.setattr("scripts.fetchLearningVocabulary.validate", lambda entries: None)
    raw = "순위\t단어\t품사\t풀이\t등급\r\n1\t가장01\t부\t\tA\r\n2\t가장02\t명\t\tC\r\n".encode("cp949")
    entries = parseSource(raw)
    assert entries[0] == {"rank": 1, "word": "가장01", "lexeme": "가장", "partOfSpeech": "부", "grade": "A"}
    assert render(entries).splitlines()[1] == "1\t가장01\t가장\t부\tA"
