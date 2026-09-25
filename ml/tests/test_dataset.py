from ml.dataset import REQUIRED_COLUMNS, assign_splits, validate_rows


def make_row(i: int, language: str = "bci", speaker: str = "spk1", **overrides) -> dict:
    row = {
        "id": f"utt{i}", "audio_path": f"data/raw/{language}/utt{i}.wav", "language": language,
        "transcription": "texte", "translation_fr": "texte", "speaker_id": speaker,
        "speaker_gender": "F", "speaker_age_range": "18-30", "dialect_variant": "",
        "duration_s": "2.5", "source": "enregistrement équipe", "license": "CC-BY-4.0",
        "consent": "oui", "annotator": "m1", "validated": "oui",
    }  # fmt: skip
    return {**row, **overrides}


def test_valid_rows():
    assert validate_rows(REQUIRED_COLUMNS, [make_row(1), make_row(2)]) == []


def test_missing_columns():
    errors = validate_rows(["id"], [])
    assert len(errors) == 1 and "Colonnes manquantes" in errors[0]


def test_detects_errors():
    rows = [
        make_row(1),
        make_row(1),  # id en double
        make_row(3, language="fra"),
        make_row(4, consent="non"),
        make_row(5, license=""),
        make_row(6, duration_s="abc"),
        make_row(7, audio_path="x.ogg"),
    ]
    errors = validate_rows(REQUIRED_COLUMNS, rows)
    assert len(errors) == 6
    for fragment in ("en double", "language", "consentement", "licence", "duration_s", "audio_path"):
        assert any(fragment in e for e in errors), fragment


def test_splits_never_share_speakers():
    rows = [make_row(i, language=lang, speaker=f"{lang}-spk{i % 20}") for lang in ("bci", "dyu") for i in range(200)]
    result = assign_splits(rows)
    speaker_splits: dict[str, set[str]] = {}
    for row in result:
        speaker_splits.setdefault(row["speaker_id"], set()).add(row["split"])
    assert all(len(s) == 1 for s in speaker_splits.values())
    # Chaque langue doit avoir les trois splits.
    for lang in ("bci", "dyu"):
        assert {r["split"] for r in result if r["language"] == lang} == {"train", "validation", "test"}


def test_splits_are_deterministic():
    rows = [make_row(i, speaker=f"spk{i % 10}") for i in range(50)]
    assert assign_splits(rows, seed=1) == assign_splits(rows, seed=1)


def test_train_is_never_empty_with_few_speakers():
    rows = [make_row(1, speaker="a"), make_row(2, speaker="b")]
    assert "train" in {r["split"] for r in assign_splits(rows)}
