import os
import json

# Paths
manual_folder = "./training_data"
auto_folder = "./llm_labels"
output_file = "merged_dataset.jsonl"


# Helper: Write a JSONL file
def write_jsonl(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


# Parser for manual dataset
def parse_manual_dataset(folder):
    dataset = []
    for file in os.listdir(folder):

        if not file.endswith(".json"):
            continue
        path = os.path.join(folder, file)
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                # print(data)
            except json.JSONDecodeError as e:
                print(f"Skipping {file} due to JSON error: {e}")
                continue

            # Adjust this part if your manual dataset keys differ
            url = data.get("url", "").strip()
            # print(url)
            user_query = data.get("user_query", "").strip()
            scraped_data = data.get("original_scrape", "")
            correct_response = data.get("correct_actions", "")

            if url and user_query and scraped_data and correct_response:
                dataset.append({
                    "instruction": f"{user_query}\n\nURL: {url}\n\nScraped Data:\n{scraped_data}",
                    "output": correct_response
                })
    print(dataset)
    return dataset


# Parser for automatic dataset
def parse_auto_dataset(folder):
    dataset = []
    for file in os.listdir(folder):
        if not file.endswith(".json"):
            continue
        path = os.path.join(folder, file)
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                print(data)
            except json.JSONDecodeError as e:
                print(f"Skipping {file} due to JSON error: {e}")
                continue

            # Adjust this mapping if automatic dataset keys differ
            url = data.get("url", "").strip()
            user_query = data.get("query", "").strip()
            scraped_data = data.get("scraped_data", "").strip() if isinstance(data.get("scraped_data"), str) else json.dumps(
                data.get("scraped_data"), ensure_ascii=False)
            correct_response = data.get("llm_response", "").strip() if isinstance(data.get("llm_response"),
                                                                                      str) else json.dumps(
                data.get("llm_response"), ensure_ascii=False)

            if url and user_query and scraped_data and correct_response:
                dataset.append({
                    "instruction": f"{user_query}\n\nURL: {url}\n\nScraped Data:\n{scraped_data}",
                    "output": correct_response
                })
    print(dataset)
    return dataset


# Main conversion
def main():
    manual_data = parse_manual_dataset(manual_folder)
    auto_data = parse_auto_dataset(auto_folder)
    combined_data = manual_data + auto_data

    print(f"Manual dataset entries: {len(manual_data)}")
    print(f"Automatic dataset entries: {len(auto_data)}")
    print(f"Total merged entries: {len(combined_data)}")

    write_jsonl(combined_data, output_file)
    print(f"Merged dataset written to {output_file}")


if __name__ == "__main__":
    main()