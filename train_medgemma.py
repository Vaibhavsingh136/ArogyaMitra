"""
MedGemma Multimodal Training Pipeline
Source: ArogyaMitra AI Radiology Fine-Tuning Module

Usage:
    python train_medgemma.py --dataset sample_dataset.json --epochs 3 --batch_size 2
"""
import os
import json
import argparse
import requests
import torch
from PIL import Image
from datasets import Dataset
from transformers import (
    AutoProcessor,
    AutoModelForImageTextToText,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

def parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune MedGemma on custom medical imaging datasets.")
    parser.add_argument("--model_id", type=str, default="google/medgemma-4b-it", help="Hugging Face Model ID")
    parser.add_argument("--dataset", type=str, default="sample_dataset.json", help="Path to JSON dataset")
    parser.add_argument("--output_dir", type=str, default="./fine_tuned_medgemma", help="Directory to save trained model")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=1, help="Per-device train batch size")
    parser.add_argument("--grad_accum", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--lora_r", type=int, default=16, help="LoRA rank dimension")
    parser.add_argument("--lora_alpha", type=int, default=32, help="LoRA alpha scaling")
    return parser.parse_args()

def load_image(image_path_or_url):
    """Loads image from local path or remote URL."""
    if str(image_path_or_url).startswith("http"):
        resp = requests.get(image_path_or_url, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
        return Image.open(resp.raw).convert("RGB")
    return Image.open(image_path_or_url).convert("RGB")

def main():
    args = parse_args()
    print("=" * 60)
    print(" MedGemma 4B Multimodal Fine-Tuning Pipeline ")
    print("=" * 60)
    print(f"Base Model:     {args.model_id}")
    print(f"Dataset File:   {args.dataset}")
    print(f"Output Path:    {args.output_dir}")
    print(f"Epochs:         {args.epochs}")
    print(f"Batch Size:     {args.batch_size} (Accum: {args.grad_accum})")
    print(f"Learning Rate:  {args.lr}")
    print("=" * 60)

    # 1. Check Device & Quantization
    is_cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {is_cuda_available}")
    
    if is_cuda_available:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True
        )
        torch_dtype = torch.bfloat16
        device_map = "auto"
    else:
        bnb_config = None
        torch_dtype = torch.float32
        device_map = "cpu"
        print("[WARNING] CUDA not detected. Training on CPU will be slow.")

    # 2. Load Processor and Base Model
    print(f"\n[1/5] Loading processor & model: {args.model_id}...")
    processor = AutoProcessor.from_pretrained(args.model_id)

    model = AutoModelForImageTextToText.from_pretrained(
        args.model_id,
        quantization_config=bnb_config,
        device_map=device_map,
        torch_dtype=torch_dtype
    )

    # 3. Setup PEFT / LoRA Adapters
    print("\n[2/5] Setting up LoRA parameter-efficient training...")
    if is_cuda_available and bnb_config is not None:
        model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 4. Load & Collate Dataset
    print(f"\n[3/5] Loading training dataset from {args.dataset}...")
    with open(args.dataset, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    dataset = Dataset.from_list(raw_data)
    print(f"Loaded {len(dataset)} training examples.")

    def collate_fn(batch):
        batch_input_ids = []
        batch_labels = []
        batch_pixel_values = []

        for item in batch:
            img = load_image(item.get("image") or item.get("image_url"))
            sys_prompt = item.get("system_prompt", "You are an expert radiologist.")
            query = item.get("user_query") or item.get("instruction")
            resp = item.get("assistant_response") or item.get("response")

            messages = [
                {"role": "system", "content": [{"type": "text", "text": sys_prompt}]},
                {"role": "user", "content": [{"type": "text", "text": query}, {"type": "image", "image": img}]},
                {"role": "assistant", "content": [{"type": "text", "text": resp}]}
            ]

            inputs = processor.apply_chat_template(
                messages,
                add_generation_prompt=False,
                tokenize=True,
                return_dict=True,
                return_tensors="pt"
            )

            input_ids = inputs["input_ids"][0]
            labels = input_ids.clone()

            # Mask prompt tokens so loss is only calculated on assistant answer
            prompt_messages = messages[:-1]
            prompt_inputs = processor.apply_chat_template(
                prompt_messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt"
            )
            prompt_len = prompt_inputs["input_ids"].shape[-1]
            labels[:prompt_len] = -100  # Ignore loss on prompt

            batch_input_ids.append(input_ids)
            batch_labels.append(labels)
            if "pixel_values" in inputs:
                batch_pixel_values.append(inputs["pixel_values"][0])

        padded_inputs = torch.nn.utils.rnn.pad_sequence(
            batch_input_ids, batch_first=True, padding_value=processor.tokenizer.pad_token_id
        )
        padded_labels = torch.nn.utils.rnn.pad_sequence(
            batch_labels, batch_first=True, padding_value=-100
        )

        batch_dict = {
            "input_ids": padded_inputs,
            "labels": padded_labels,
            "attention_mask": (padded_inputs != processor.tokenizer.pad_token_id).long()
        }

        if batch_pixel_values:
            batch_dict["pixel_values"] = torch.stack(batch_pixel_values)

        return batch_dict

    # 5. Training Configuration
    print("\n[4/5] Configuring Training Arguments...")
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        logging_steps=1,
        save_strategy="epoch",
        fp16=False,
        bf16=is_cuda_available,
        optim="paged_adamw_8bit" if is_cuda_available else "adamw_torch",
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=collate_fn
    )

    # 6. Execute Training
    print("\n[5/5] Starting Model Training...")
    trainer.train()

    # 7. Save Artifacts
    print(f"\nSaving fine-tuned LoRA weights to {args.output_dir}...")
    model.save_pretrained(args.output_dir)
    processor.save_pretrained(args.output_dir)
    print("=" * 60)
    print("Training finished! You can now run inference with inference_medgemma.py.")
    print("=" * 60)

if __name__ == "__main__":
    main()
