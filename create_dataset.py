import json
import os
from pathlib import Path

def create_dataset():
    dataset = []

    # Process llm_labels folder
    llm_labels_path = Path("llm_labels")
    for json_file in llm_labels_path.glob("label_*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if data.get("correct", False):
                actions = data.get("actions", [])
                verbal_guide = data.get("verbal_guide", "")
                if actions or verbal_guide:
                    # Create instruction
                    query = data["query"]
                    url = data["url"]
                    scraped_data = data["scraped_data"]

                    instruction = f"{query}\n\nURL: {url}\n\nScraped Data:\n{json.dumps(scraped_data)}"

                    # Create output
                    output = json.dumps({
                        "action_sequence": actions,
                        "verbal_guide": verbal_guide
                    })

                    dataset.append({
                        "instruction": instruction,
                        "output": output
                    })

        except Exception as e:
            print(f"Error processing {json_file}: {e}")

    # Process training_data folder
    training_data_path = Path("training_data")
    for json_file in training_data_path.glob("session_*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            correct_actions = data.get("correct_actions", [])
            if correct_actions:
                # Create instruction
                url = data["url"]
                scraped_data = data["original_scrape"]

                # For training_data, we don't have query, so use a generic one or skip
                # Since no query, perhaps skip or use a placeholder
                query = "Perform the required action on this webpage"  # Placeholder

                instruction = f"{query}\n\nURL: {url}\n\nScraped Data:\n{json.dumps(scraped_data)}"

                # Create output with action_sequence only
                output = json.dumps({
                    "action_sequence": correct_actions,
                    "verbal_guide": ""  # Empty verbal guide
                })

                dataset.append({
                    "instruction": instruction,
                    "output": output
                })

        except Exception as e:
            print(f"Error processing {json_file}: {e}")

    # Write to json file
    with open("new_dataset.json", 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"Dataset created with {len(dataset)} entries.")

if __name__ == "__main__":
    create_dataset()