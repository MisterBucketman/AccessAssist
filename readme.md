# ScrapyDS / Accessibility Assistant

AI-powered accessibility assistant that helps users accomplish tasks on websites by suggesting and executing step-by-step actions (click, fill, navigate). It uses local LLM (Ollama), Playwright for scraping and execution, and a human-in-the-loop pipeline to collect and merge training data for fine-tuning.

## What it does

1. **Process request**: Enter a URL and a natural-language query (e.g. “Search for cat food”). The app (1) gets scraped data (from cache if “Use cached scrape” is checked and available, else scrapes and caches), (2) sends the structure and query to an LLM (Ollama/Llama 3), and returns an action sequence plus verbal guidance. **Scrape page only** scrapes and caches without calling the LLM.
2. **Label**: Mark LLM results as correct or incorrect; labels are saved under `llm_labels/`.
3. **Manual recording**: Record correct actions by performing them in a browser; sessions are saved under `training_data/`.
4. **Execute**: Run the suggested actions in a browser and see per-step success/failure.
5. **Speak**: Read the verbal guide aloud (TTS).
6. **Merge & train**: Merge manual and (correct-only) auto labels into a single JSONL, then fine-tune a model (QLoRA) for better behavior.

## Quick start

### Prerequisites

- Python 3.9+
- [Ollama](https://ollama.ai/) with a model (e.g. `ollama pull llama3`)
- Playwright browsers: `playwright install chromium`

### Run the app

```bash
pip install -r requirements.txt
python app.py
```

- **Accessibility Assistant**: http://127.0.0.1:5000/

### Optional: test website

Serve the included test site to try flows (subscribe, search, etc.):

```bash
python -m http.server 8000
```

- **Test site**: http://localhost:8000/index.html (use this URL in the assistant when testing)

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3` | Ollama model name |
| `HEADLESS` | `true` | Scraper: `true` = no browser window, `false` = show browser |
| `SCRAPE_SCROLL_STEPS` | `20` | Scroll steps for lazy-loaded content |
| `SCRAPE_TIMEOUT_MS` | `60000` | Page load timeout (ms) |
| `MANUAL_DATA_DIR` | `./training_data` | Manual session JSONs |
| `AUTO_LABELS_DIR` | `./llm_labels` | Label JSONs from UI |
| `MERGED_OUTPUT` | `merged_dataset.jsonl` | Output of merge script |
| `SCRAPE_CACHE_DIR` | `scrape_cache` | Directory for cached scraped page data |
| `TRAIN_*` | see `config.py` | Trainer paths and hyperparams |

## Scrape cache

Scraped page data is cached by URL so the same page does not need to be scraped repeatedly.

- **Use cached scrape if available**: When checked, “Process Request” uses cached scraped data for the current URL when present; otherwise it scrapes and then caches.
- **Scrape page only**: Scrapes the URL and saves to cache without calling the LLM. Use this to pre-populate the cache, then run “Process Request” with “Use cached scrape” to run the LLM only and save manual testing time.
- Cache is stored under `scrape_cache/` (or `SCRAPE_CACHE_DIR`). Each entry is keyed by normalized URL (scheme + host + path + query, no fragment).

## Data pipeline

1. **Collect data**
   - Use the UI to label LLM results (correct/incorrect) and/or record manual sessions.
2. **Merge**
   ```bash
   python merge_datasets.py
   ```
   - Reads `training_data/` and `llm_labels/` (only labels with `correct === true`).
   - Writes normalized `merged_dataset.jsonl` (see schema below).
3. **Train**
   ```bash
   pip install -r requirements-train.txt
   python trainer.py --data_files merged_dataset.jsonl [--epochs 3] [--save_merged]
   ```
   - Options: `--data_files`, `--model_name`, `--output_dir`, `--lora_output`, `--merged_output`, `--epochs`, `--batch_size`, `--save_merged`, `--no_train`.

## Merged dataset schema (merged_dataset.jsonl)

Each line is a JSON object with:

- **instruction** (string): `"{user_query}\n\nURL: {url}\n\nScraped Data:\n{scraped_data}"`
- **output** (object): normalized shape for training:
  - `action_sequence` (list): `[{ "action": "click"|"fill"|"navigate", "target": "...", "value"?: "..." }, ...]`
  - `verbal_guide` (string): step-by-step instructions

Manual and auto pipelines both emit this same output shape.

## Project layout

| File / folder | Role |
|---------------|------|
| `app.py` | Flask app: process, label, manual record, execute, speak |
| `scraper.py` | Playwright scraper for interactive elements |
| `ollama_integration.py` | LLM prompt and response parsing (Ollama) |
| `executor.py` | Playwright execution of action sequences |
| `merge_datasets.py` | Merge manual + auto labels → JSONL |
| `trainer.py` | QLoRA fine-tuning (CLI) |
| `config.py` | Central config from env |
| `templates/index.html` | Assistant UI |
| `test_website/` | Local test pages |

## License

Use as needed for your project.
