from datasets import load_dataset

dataset = load_dataset("json", data_files="merged_dataset.jsonl")
print(dataset)

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

model_name = "meta-llama/Meta-Llama-3-8B"  # Adjust if using local path or Ollama weights

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token

# Load model in 4-bit precision (QLoRA)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    load_in_4bit=True,
    device_map="auto"
)

# Setup LoRA config for QLoRA fine-tuning
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# Apply LoRA to the model
model = get_peft_model(model, lora_config)

def tokenize_function(examples):
    # Concatenate instruction and output, separated by EOS token
    inputs = [inst for inst in examples["instruction"]]
    outputs = [out for out in examples["output"]]
    model_inputs = tokenizer(inputs, max_length=512, truncation=True, padding="max_length")
    labels = tokenizer(outputs, max_length=512, truncation=True, padding="max_length")

    # For causal LM, labels are inputs shifted by one; so labels = tokenized output tokens
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

tokenized_dataset = dataset.map(tokenize_function, batched=True)

from transformers import Trainer, TrainingArguments

training_args = TrainingArguments(
    output_dir="./llama3-qlora-finetuned",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    num_train_epochs=3,
    learning_rate=2e-4,
    fp16=True,               # Enable mixed precision if your GPU supports it
    logging_steps=5,
    save_strategy="epoch",
    save_total_limit=1,
    report_to="none"
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    tokenizer=tokenizer
)

trainer.train()

model.save_pretrained("./llama3-playwright-lora")

from transformers import AutoModelForCausalLM
from peft import PeftModel

base_model = AutoModelForCausalLM.from_pretrained(model_name)
model = PeftModel.from_pretrained(base_model, "./llama3-playwright-lora")
model.save_pretrained("./llama3-playwright-merged")