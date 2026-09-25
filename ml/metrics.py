"""Métriques d'évaluation, sans dépendance externe.

- Détection de langue (LID) : exactitude, matrice de confusion, F1 par langue.
- Transcription (STT)       : WER (taux d'erreur mots) et CER (taux d'erreur caractères).
La traduction (BLEU/chrF) sera évaluée avec `sacrebleu` (voir docs/05-strategie-ml.md).
"""

import unicodedata
from collections import Counter
from collections.abc import Sequence


def normalize_text(text: str) -> str:
    """Normalisation minimale avant calcul du WER/CER : Unicode NFC, minuscules,
    ponctuation retirée, espaces normalisés. Les diacritiques (tons, voyelles
    ouvertes ɛ/ɔ) sont CONSERVÉS : ils sont porteurs de sens en Baoulé et Dioula."""
    text = unicodedata.normalize("NFC", text).lower()
    # On retire ponctuation (P*) et symboles (S*) par catégorie Unicode, et non avec \w :
    # les diacritiques combinants (catégorie M*, ex. tilde de nasalisation) ne sont pas
    # des \w et seraient supprimés à tort. L'apostrophe est gardée (élisions).
    text = "".join(" " if unicodedata.category(c)[0] in "PS" and c != "'" else c for c in text)
    return " ".join(text.split())


def edit_distance(ref: Sequence, hyp: Sequence) -> int:
    """Distance de Levenshtein (substitutions, insertions, suppressions)."""
    previous = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, start=1):
        current = [i]
        for j, h in enumerate(hyp, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (r != h)))
        previous = current
    return previous[-1]


def _error_rate(refs: Sequence[Sequence], hyps: Sequence[Sequence]) -> float:
    if len(refs) != len(hyps):
        raise ValueError("refs et hyps doivent avoir la même longueur")
    total = sum(len(r) for r in refs)
    if total == 0:
        raise ValueError("Les références sont vides")
    return sum(edit_distance(r, h) for r, h in zip(refs, hyps, strict=True)) / total


def wer(references: Sequence[str], hypotheses: Sequence[str]) -> float:
    """Word Error Rate agrégé sur le corpus (et non moyenne des WER par phrase)."""
    return _error_rate([normalize_text(r).split() for r in references], [normalize_text(h).split() for h in hypotheses])


def cer(references: Sequence[str], hypotheses: Sequence[str]) -> float:
    """Character Error Rate agrégé sur le corpus."""
    return _error_rate([normalize_text(r) for r in references], [normalize_text(h) for h in hypotheses])


def classification_report(y_true: Sequence[str], y_pred: Sequence[str]) -> dict:
    """Exactitude, matrice de confusion et précision/rappel/F1 par classe."""
    if len(y_true) != len(y_pred) or not y_true:
        raise ValueError("y_true et y_pred doivent être non vides et de même longueur")
    labels = sorted(set(y_true) | set(y_pred))
    confusion = Counter(zip(y_true, y_pred, strict=True))
    per_class = {}
    for label in labels:
        tp = confusion[(label, label)]
        fp = sum(confusion[(t, label)] for t in labels if t != label)
        fn = sum(confusion[(label, p)] for p in labels if p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
    return {
        "accuracy": sum(confusion[(label, label)] for label in labels) / len(y_true),
        "confusion": {t: {p: confusion[(t, p)] for p in labels} for t in labels},
        "per_class": per_class,
    }
