"""Central config via environment variables with defaults. Used by app, scraper, ollama, merge, trainer."""
import os


def _bool(val, default=False):
    if val is None or val == "":
        return default
    return str(val).lower() in ("1", "true", "yes")


def _int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


# Ollama
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")

# Scraper
HEADLESS = _bool(os.environ.get("HEADLESS"), True)
SCRAPE_SCROLL_STEPS = _int(os.environ.get("SCRAPE_SCROLL_STEPS"), 20)
SCRAPE_TIMEOUT_MS = _int(os.environ.get("SCRAPE_TIMEOUT_MS"), 60000)

# Merge
MANUAL_DATA_DIR = os.environ.get("MANUAL_DATA_DIR", "./training_data")
AUTO_LABELS_DIR = os.environ.get("AUTO_LABELS_DIR", "./llm_labels")
MERGED_OUTPUT = os.environ.get("MERGED_OUTPUT", "merged_dataset.jsonl")

# Trainer
TRAIN_DATA_FILES = os.environ.get("TRAIN_DATA_FILES", "merged_dataset.jsonl")
TRAIN_MODEL_NAME = os.environ.get("TRAIN_MODEL_NAME", "meta-llama/Meta-Llama-3-8B")
TRAIN_OUTPUT_DIR = os.environ.get("TRAIN_OUTPUT_DIR", "./llama3-qlora-finetuned")
TRAIN_LORA_OUTPUT = os.environ.get("TRAIN_LORA_OUTPUT", "./llama3-playwright-lora")
TRAIN_MERGED_OUTPUT = os.environ.get("TRAIN_MERGED_OUTPUT", "./llama3-playwright-merged")
TRAIN_BATCH_SIZE = _int(os.environ.get("TRAIN_BATCH_SIZE"), 1)
TRAIN_GRADIENT_ACCUMULATION = _int(os.environ.get("TRAIN_GRADIENT_ACCUMULATION"), 4)
TRAIN_EPOCHS = _int(os.environ.get("TRAIN_EPOCHS"), 3)
TRAIN_LEARNING_RATE = float(os.environ.get("TRAIN_LEARNING_RATE", "2e-4"))
TRAIN_MAX_LENGTH = _int(os.environ.get("TRAIN_MAX_LENGTH"), 512)
