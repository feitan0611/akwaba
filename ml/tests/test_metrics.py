import pytest

from ml.metrics import cer, classification_report, edit_distance, normalize_text, wer


def test_edit_distance():
    assert edit_distance("chat", "chats") == 1
    assert edit_distance(["a", "b", "c"], ["a", "c"]) == 1
    assert edit_distance("", "abc") == 3


def test_normalize_keeps_diacritics_and_open_vowels():
    assert normalize_text("  Ɔ   KƐ̃, ní!  ") == "ɔ kɛ̃ ní"


def test_wer_perfect_and_errors():
    assert wer(["a b c d"], ["a b c d"]) == 0
    assert wer(["a b c d"], ["a x c"]) == pytest.approx(2 / 4)


def test_wer_is_corpus_level():
    # 1 erreur sur 1 mot + 0 erreur sur 3 mots = 1/4, pas la moyenne (1 + 0) / 2.
    assert wer(["a", "b c d"], ["x", "b c d"]) == pytest.approx(1 / 4)


def test_cer():
    assert cer(["abcd"], ["abxd"]) == pytest.approx(1 / 4)


def test_classification_report():
    report = classification_report(["bci", "bci", "dyu", "dyu"], ["bci", "dyu", "dyu", "dyu"])
    assert report["accuracy"] == 0.75
    assert report["confusion"]["bci"]["dyu"] == 1
    assert report["per_class"]["dyu"]["recall"] == 1.0
    assert report["per_class"]["bci"]["recall"] == 0.5
