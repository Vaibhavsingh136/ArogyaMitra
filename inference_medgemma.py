"""
MedGemma Fine-Tuned Model Inference Script
Loads trained LoRA weights and performs clinical radiological analysis.

Usage:
    python inference_medgemma.py --image "path_or_url_to_xray.png" --prompt "Describe this X-ray"
"""
import argparse
import requests
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText
from peft import PeftModel

def parse_args():
    parser = argparse.ArgumentParser(description="Run inference with fine-tuned MedGemma.")
    parser.add_argument("--base_model", type=str, default="google/medgemma-4b-it", help="Base model ID")
    parser.add_argument("--adapter_dir", type=str, default="./fine_tuned_medgemma", help="Directory containing saved LoRA weights")
    parser.add_argument("--image", type=str, default="https://upload.wikimedia.org/wikipedia/commons/c/c8/Chest_Xray_PA_3-8-2010.png", help="Image path or URL")
    parser.add_argument("--prompt", type=str, default="Describe this X-ray and write findings and impression:", help="Clinical prompt")
    parser.add_argument("--max_tokens", type=int, default=250, help="Maximum new tokens to generate")
    return parser.parse_args()

def load_image(image_path_or_url):
    if str(image_path_or_url).startswith("http"):
        resp = requests.get(image_path_or_url, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
        return Image.open(resp.raw).convert("RGB")
    return Image.open(image_path_or_url).convert("RGB")

def main():
    args = parse_args()
    print("=" * 60)
    print(" MedGemma Radiology Clinical Inference ")
    print("=" * 60)
    print(f"Base Model:   {args.base_model}")
    print(f"LoRA Adapter: {args.adapter_dir}")
    print(f"Image Source: {args.image}")
    print("=" * 60)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

    # 1. Load Processor
    try:
        processor = AutoProcessor.from_pretrained(args.adapter_dir)
    except Exception:
        processor = AutoProcessor.from_pretrained(args.base_model)

    # 2. Load Base Model
    print("Loading base model...")
    base_model = AutoModelForImageTextToText.from_pretrained(
        args.base_model,
        torch_dtype=torch_dtype,
        device_map="auto" if torch.cuda.is_available() else None,
    )

    # 3. Load Trained LoRA Weights
    print(f"Applying fine-tuned LoRA weights from {args.adapter_dir}...")
    try:
        model = PeftModel.from_pretrained(base_model, args.adapter_dir)
    except Exception as e:
        print(f"[NOTE] Adapter not loaded ({e}). Using base model directly.")
        model = base_model

    model.eval()

    # 4. Prepare Image & Messages
    image = load_image(args.image)
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are an expert radiologist."}]
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": args.prompt},
                {"type": "image", "image": image}
            ]
        }
    ]

    # 5. Tokenize using apply_chat_template
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt"
    ).to(device, dtype=torch_dtype)

    input_len = inputs["input_ids"].shape[-1]

    # 6. Generate Response
    print("\nGenerating AI Clinical Diagnosis...")
    with torch.inference_mode():
        generation = model.generate(**inputs, max_new_tokens=args.max_tokens, do_sample=False)
        generation = generation[0][input_len:]

    decoded = processor.decode(generation, skip_special_tokens=True)

    print("\n" + "=" * 60)
    print(" AI RADIOLOGY REPORT ")
    print("=" * 60)
    print(decoded)
    print("=" * 60)

if __name__ == "__main__":
    main()
