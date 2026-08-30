from hanlint.data import gradesByLexeme, vocabularyEntries, vocabularyMetadata


def testOfficialVocabularyProjectionHasExpectedShape():
    entries = vocabularyEntries()
    assert len(entries) == 5965
    assert sum(entry.grade == "A" for entry in entries) == 982
    assert sum(entry.grade == "B" for entry in entries) == 2111
    assert sum(entry.grade == "C" for entry in entries) == 2872
    assert len(gradesByLexeme()) == 5543
    assert gradesByLexeme()["가장"] == ("A", "C")


def testVocabularyMetadataStatesAudienceAndLicense():
    metadata = vocabularyMetadata()
    assert metadata["dataset"]["license"] == "공공누리 제1유형"
    assert metadata["dataset"]["personalData"] is False
    assert "한국어 학습자용" in metadata["traps"]["audience"]
