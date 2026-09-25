"""Validation du fichier de métadonnées du corpus et découpage train/validation/test.

Usage :
    python -m ml.dataset validate data/metadata/metadata.csv [--check-audio --audio-root .]
    python -m ml.dataset split    data/metadata/metadata.csv data/metadata/metadata_split.csv

Le schéma des colonnes est documenté dans docs/04-donnees.md.
"""

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

REQUIRED_COLUMNS = [
    "id", "audio_path", "language", "transcription", "translation_fr",
    "speaker_id", "speaker_gender", "speaker_age_range", "dialect_variant",
    "duration_s", "source", "license", "consent", "annotator", "validated",
]  # fmt: skip
LANGUAGES = {"bci", "dyu"}
GENDERS = {"F", "M", "NR"}  # NR = non renseigné
YES_NO = {"oui", "non"}
SPLITS = ("train", "validation", "test")


def read_rows(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def validate_rows(columns: list[str], rows: list[dict], base_dir: Path | None = None) -> list[str]:
    """Retourne la liste des erreurs (vide si le fichier est valide).
    Si base_dir est fourni, vérifie aussi que chaque fichier audio existe."""
    missing = [c for c in REQUIRED_COLUMNS if c not in columns]
    if missing:
        return [f"Colonnes manquantes : {', '.join(missing)}"]

    errors: list[str] = []
    seen_ids: set[str] = set()
    for line, row in enumerate(rows, start=2):  # ligne 1 = en-tête
        where = f"ligne {line} (id={row['id']!r})"
        if not row["id"]:
            errors.append(f"{where} : id vide")
        elif row["id"] in seen_ids:
            errors.append(f"{where} : id en double")
        seen_ids.add(row["id"])

        if row["language"] not in LANGUAGES:
            errors.append(f"{where} : language doit être dans {sorted(LANGUAGES)}")
        if not row["transcription"].strip():
            errors.append(f"{where} : transcription vide")
        if not row["speaker_id"].strip():
            errors.append(f"{where} : speaker_id vide (indispensable pour éviter les fuites entre splits)")
        if row["speaker_gender"] not in GENDERS:
            errors.append(f"{where} : speaker_gender doit être dans {sorted(GENDERS)}")
        # Exigences éthiques et légales : source, licence et consentement obligatoires.
        if not row["source"].strip():
            errors.append(f"{where} : source non documentée")
        if not row["license"].strip():
            errors.append(f"{where} : licence non documentée")
        if row["consent"] != "oui":
            errors.append(f"{where} : consentement absent (consent doit valoir 'oui')")
        if row["validated"] not in YES_NO:
            errors.append(f"{where} : validated doit valoir 'oui' ou 'non'")
        try:
            if float(row["duration_s"]) <= 0:
                raise ValueError
        except ValueError:
            errors.append(f"{where} : duration_s doit être un nombre > 0")
        if not row["audio_path"].lower().endswith((".wav", ".mp3")):
            errors.append(f"{where} : audio_path doit être un .wav ou .mp3")
        elif base_dir is not None and not (base_dir / row["audio_path"]).is_file():
            errors.append(f"{where} : fichier audio introuvable ({row['audio_path']})")
        if "split" in row and row["split"] and row["split"] not in SPLITS:
            errors.append(f"{where} : split doit être dans {SPLITS}")
    return errors


def assign_splits(rows: list[dict], ratios: tuple[float, float, float] = (0.8, 0.1, 0.1), seed: int = 42) -> list[dict]:
    """Découpe par LOCUTEUR (jamais le même locuteur dans deux splits) et par langue.

    Découper par phrase ferait fuiter la voix des locuteurs du test dans l'entraînement
    et surestimerait les performances. Le découpage est déterministe (graine fixe).
    """
    if abs(sum(ratios) - 1) > 1e-9:
        raise ValueError("Les ratios doivent sommer à 1")

    speakers_by_lang: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        speakers_by_lang[row["language"]][row["speaker_id"]] += float(row["duration_s"])

    speaker_split: dict[tuple[str, str], str] = {}
    rng = random.Random(seed)
    for language in sorted(speakers_by_lang):
        durations = speakers_by_lang[language]
        speakers = sorted(durations)
        rng.shuffle(speakers)
        total = sum(durations.values())
        filled = {split: 0.0 for split in SPLITS}
        # Remplissage glouton : chaque locuteur va dans le split le plus en retard sur son
        # objectif de durée. En cas d'égalité, l'ordre de SPLITS fait passer train en premier.
        for speaker in speakers:
            split = min(
                SPLITS,
                key=lambda s: filled[s] / (ratios[SPLITS.index(s)] * total) if ratios[SPLITS.index(s)] else 1e9,
            )
            speaker_split[(language, speaker)] = split
            filled[split] += durations[speaker]

    return [{**row, "split": speaker_split[(row["language"], row["speaker_id"])]} for row in rows]


def split_summary(rows: list[dict]) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        summary[f"{row['language']}/{row['split']}"]["duration_s"] += float(row["duration_s"])
        summary[f"{row['language']}/{row['split']}"]["utterances"] += 1
    return {k: dict(v) for k, v in sorted(summary.items())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_val = sub.add_parser("validate", help="Valider un fichier de métadonnées")
    p_val.add_argument("metadata", type=Path)
    p_val.add_argument("--check-audio", action="store_true", help="Vérifier l'existence des fichiers audio")
    p_val.add_argument("--audio-root", type=Path, default=Path("."), help="Racine des chemins audio_path")
    p_split = sub.add_parser("split", help="Ajouter une colonne split (train/validation/test)")
    p_split.add_argument("metadata", type=Path)
    p_split.add_argument("output", type=Path)
    p_split.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    columns, rows = read_rows(args.metadata)
    base_dir = args.audio_root if getattr(args, "check_audio", False) else None
    errors = validate_rows(columns, rows, base_dir)
    if errors:
        print(f"{len(errors)} erreur(s) dans {args.metadata} :", *errors, sep="\n  - ", file=sys.stderr)
        return 1
    print(f"OK : {len(rows)} enregistrement(s) valides.")

    if args.command == "split":
        rows = assign_splits(rows, seed=args.seed)
        out_columns = columns if "split" in columns else [*columns, "split"]
        with args.output.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=out_columns)
            writer.writeheader()
            writer.writerows(rows)
        summary = split_summary(rows)
        for key, stats in summary.items():
            print(f"  {key:<16} {int(stats['utterances']):>5} énoncés  {stats['duration_s'] / 60:>7.1f} min")
        for language in sorted({row["language"] for row in rows}):
            empty = [s for s in SPLITS if f"{language}/{s}" not in summary]
            if empty:
                print(f"ATTENTION : {language} n'a aucun locuteur en {', '.join(empty)} (pas assez de locuteurs).")
        print(f"Écrit : {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
