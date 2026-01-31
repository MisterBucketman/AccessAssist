"""
Merge manual (training_data/) and auto (llm_labels/) datasets into a single JSONL
for fine-tuning. Output format is normalized: each line has "instruction" and "output"
where output is always {"action_sequence": [...], "verbal_guide": "..."}.
Auto labels are included only when correct === true.
"""
import os
import json

# Paths (override via env or keep defaults)
manual_folder = os.environ.get("MANUAL_DATA_DIR", "./training_data")
auto_folder = os.environ.get("AUTO_LABELS_DIR", "./llm_labels")
output_file = os.environ.get("MERGED_OUTPUT", "merged_dataset.jsonl")


def write_jsonl(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def normalize_output(action_sequence, verbal_guide=""):
    """Ensure output has consistent shape for training."""
    if not isinstance(action_sequence, list):
        action_sequence = []
    return {"action_sequence": action_sequence, "verbal_guide": verbal_guide or ""}


def parse_manual_dataset(folder):
    dataset = []
    if not os.path.isdir(folder):
        return dataset
    for file in os.listdir(folder):
        if not file.endswith(".json"):
            continue
        path = os.path.join(folder, file)
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Skipping {file} due to JSON error: {e}")
                continue

        url = data.get("url", "").strip()
        user_query = data.get("user_query", "").strip()
        scraped_data = data.get("original_scrape", "")
        correct_actions = data.get("correct_actions", [])

        if url and user_query and scraped_data is not None and correct_actions is not None:
            scraped_str = scraped_data if isinstance(scraped_data, str) else json.dumps(scraped_data, ensure_ascii=False)
            output = normalize_output(correct_actions, verbal_guide="")
            dataset.append({
                "instruction": f"{user_query}\n\nURL: {url}\n\nScraped Data:\n{scraped_str}",
                "output": output
            })
    return dataset


def parse_auto_dataset(folder, only_correct=True):
    """Parse llm_labels. When only_correct=True, include only entries with correct === true."""
    dataset = []
    if not os.path.isdir(folder):
        return dataset
    for file in os.listdir(folder):
        if not file.endswith(".json"):
            continue
        path = os.path.join(folder, file)
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Skipping {file} due to JSON error: {e}")
                continue

        if only_correct and "correct" in data and data["correct"] is not True:
            continue

        url = data.get("url", "").strip()
        user_query = data.get("query", "").strip()
        scraped_data = data.get("scraped_data")
        llm_response = data.get("llm_response")

        if not url or not user_query:
            continue

        scraped_str = scraped_data
        if scraped_str is None:
            continue
        if not isinstance(scraped_str, str):
            scraped_str = json.dumps(scraped_str, ensure_ascii=False)

        if llm_response is None:
            continue
        if isinstance(llm_response, str):
            try:
                llm_response = json.loads(llm_response)
            except json.JSONDecodeError:
                continue
        action_sequence = llm_response.get("action_sequence") if isinstance(llm_response, dict) else None
        verbal_guide = llm_response.get("verbal_guide", "") if isinstance(llm_response, dict) else ""
        if action_sequence is None:
            action_sequence = []

        output = normalize_output(action_sequence, verbal_guide)
        dataset.append({
            "instruction": f"{user_query}\n\nURL: {url}\n\nScraped Data:\n{scraped_str}",
            "output": output
        })
    return dataset


def main():
    manual_data = parse_manual_dataset(manual_folder)
    auto_data = parse_auto_dataset(auto_folder, only_correct=True)
    combined_data = manual_data + auto_data

    print(f"Manual dataset entries: {len(manual_data)}")
    print(f"Automatic dataset entries (correct only): {len(auto_data)}")
    print(f"Total merged entries: {len(combined_data)}")

    write_jsonl(combined_data, output_file)
    print(f"Merged dataset written to {output_file}")


if __name__ == "__main__":
    main()
