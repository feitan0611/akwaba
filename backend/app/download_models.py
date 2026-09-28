"""Télécharge les modèles du moteur « local » (≈ 6 Go) dans le cache Hugging Face.

Usage (depuis la racine du projet) :
    python -m app.download_models --app-dir backend        # ou : cd backend && python -m app.download_models

- Seuls les fichiers réellement utilisés sont téléchargés (ex. le seul adaptateur Dioula de
  MMS, pas ceux des 1 100 autres langues).
- Le téléchargement REPREND là où il s'était arrêté en cas de coupure : relancer la commande.
- Le LLM est géré à part par Ollama :  ollama pull qwen2.5:3b
"""

import sys
import time

FILES = {
    "facebook/mms-1b-all": [
        "config.json",
        "preprocessor_config.json",
        "special_tokens_map.json",
        "tokenizer_config.json",
        "vocab.json",
        "adapter.dyu.safetensors",
        "model.safetensors",  # 3,7 Go
    ],
    "facebook/nllb-200-distilled-600M": [
        "config.json",
        "generation_config.json",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "sentencepiece.bpe.model",
        "pytorch_model.bin",  # 2,3 Go
    ],
    "facebook/mms-tts-dyu": [
        "config.json",
        "special_tokens_map.json",
        "tokenizer_config.json",
        "vocab.json",
        "model.safetensors",
    ],
}


def main() -> int:
    from huggingface_hub import hf_hub_download

    from app.services.local import use_system_certificates

    use_system_certificates()

    total = sum(len(files) for files in FILES.values())
    done = 0
    start = time.time()
    for repo, files in FILES.items():
        for filename in files:
            done += 1
            print(f"[{done}/{total}] {repo}/{filename}", flush=True)
            for attempt in range(1, 6):
                try:
                    hf_hub_download(repo, filename)
                    break
                except Exception as exc:  # coupure réseau : on réessaie (reprise automatique)
                    print(f"    échec (tentative {attempt}/5) : {exc}", flush=True)
                    time.sleep(10 * attempt)
            else:
                print("Abandon : relancez la commande plus tard, le téléchargement reprendra.", flush=True)
                return 1
    print(f"Terminé en {(time.time() - start) / 60:.0f} min. Pensez aussi à : ollama pull qwen2.5:3b", flush=True)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
