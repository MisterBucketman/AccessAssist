"""
QLoRA fine-tuning for accessibility assistant. Loads merged_dataset.jsonl (instruction + output),
tokenizes, trains, saves LoRA and optionally merged weights.
Usage: python trainer.py [--data_files FILE] [--output_dir DIR] [--epochs N] ...
"""
import argparse
import json
from pathlib import Path

from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model, PeftModel

from config import (
    TRAIN_DATA_FILES,
    TRAIN_MODEL_NAME,
    TRAIN_OUTPUT_DIR,
    TRAIN_LORA_OUTPUT,
    TRAIN_MERGED_OUTPUT,
    TRAIN_BATCH_SIZE,
    TRAIN_GRADIENT_ACCUMULATION,
    TRAIN_EPOCHS,
    TRAIN_LEARNING_RATE,
    TRAIN_MAX_LENGTH,
)


def parse_args():
    p = argparse.ArgumentParser(description="QLoRA fine-tune LLaMA for accessibility assistant")
    p.add_argument("--data_files", default=TRAIN_DATA_FILES, help="Path to merged JSONL")
    p.add_argument("--model_name", default=TRAIN_MODEL_NAME, help="Base model name or path")
    p.add_argument("--output_dir", default=TRAIN_OUTPUT_DIR, help="Training output dir")
    p.add_argument("--lora_output", default=TRAIN_LORA_OUTPUT, help="LoRA adapter save path")
    p.add_argument("--merged_output", default=TRAIN_MERGED_OUTPUT, help="Merged model save path")
    p.add_argument("--epochs", type=int, default=TRAIN_EPOCHS)
    p.add_argument("--batch_size", type=int, default=TRAIN_BATCH_SIZE)
    p.add_argument("--gradient_accumulation_steps", type=int, default=TRAIN_GRADIENT_ACCUMULATION)
    p.add_argument("--learning_rate", type=float, default=TRAIN_LEARNING_RATE)
    p.add_argument("--max_length", type=int, default=TRAIN_MAX_LENGTH)
    p.add_argument("--save_merged", action="store_true", help="Save merged base+LoRA model")
    p.add_argument("--no_train", action="store_true", help="Only load and tokenize, no training")
    return p.parse_args()


def load_and_tokenize(data_files, model_name, max_length):
    """Load JSONL and tokenize instruction + output. Output may be dict or list; serialized to JSON string."""
    dataset = load_dataset("json", data_files=data_files)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token

    def tokenize_function(examples):
        inputs = list(examples["instruction"])
        outputs = list(examples["output"])
        # Normalize output to string (merged_dataset output is dict {action_sequence, verbal_guide})
        out_strs = []
        for out in outputs:
            if isinstance(out, (dict, list)):
                out_strs.append(json.dumps(out, ensure_ascii=False))
            else:
                out_strs.append(str(out))
        model_inputs = tokenizer(
            inputs, max_length=max_length, truncation=True, padding="max_length"
        )
        labels = tokenizer(
            out_strs, max_length=max_length, truncation=True, padding="max_length"
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    tokenized = dataset.map(tokenize_function, batched=True)
    return tokenizer, tokenized


def train(args):
    data_files = args.data_files
    if not Path(data_files).exists():
        raise FileNotFoundError(f"Data file not found: {data_files}. Run merge_datasets.py first.")

    tokenizer, tokenized = load_and_tokenize(
        data_files, args.model_name, args.max_length
    )
    train_dataset = tokenized["train"]

    if args.no_train:
        print("Loaded and tokenized; --no_train set, exiting.")
        return

    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        load_in_4bit=True,
        device_map="auto"
    )
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        fp16=True,
        logging_steps=5,
        save_strategy="epoch",
        save_total_limit=1,
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        tokenizer=tokenizer
    )
    trainer.train()
    model.save_pretrained(args.lora_output)
    print(f"LoRA adapter saved to {args.lora_output}")

    if args.save_merged:
        base_model = AutoModelForCausalLM.from_pretrained(args.model_name)
        merged = PeftModel.from_pretrained(base_model, args.lora_output)
        merged.save_pretrained(args.merged_output)
        print(f"Merged model saved to {args.merged_output}")


if __name__ == "__main__":
    train(parse_args())
