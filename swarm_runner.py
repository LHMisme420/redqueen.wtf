#!/usr/bin/env python3
"""
Red Queen Swarm Runner v0.1
Load target model, unleash attacks, compute lethality.
Usage: python swarm_runner.py --target meta-llama/Llama-3.1-405B --budget 1e24
"""

import os
import sys
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from accelerate import Accelerator
from pydantic import BaseModel, ValidationError
import argparse
import json
from datetime import datetime
from ecdsa import SigningKey, VerifyingKey, SECP256k1
import hashlib

# Local imports (fix paths if needed)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from schema.provenance import Provenance

class AttackResult(BaseModel):
    attack_id: str
    prompt: str
    response: str
    success: bool
    keywords_triggered: list

def load_attacks():
    attacks = []
    attacks_dir = os.path.join(os.path.dirname(__file__), 'attacks')
    for file in os.listdir(attacks_dir):
        if file.endswith('.py') and not file.startswith('__'):
            module_name = file[:-3]
            module = __import__(f'attacks.{module_name}', fromlist=[''])
            attacks.append(module)
    return attacks

def load_model(target_model: str):
    accelerator = Accelerator()
    model = AutoModelForCausalLM.from_pretrained(
        target_model,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        load_in_4bit=True
    )
    tokenizer = AutoTokenizer.from_pretrained(target_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model, tokenizer = accelerator.prepare(model, tokenizer)
    return model, tokenizer, accelerator

def run_single_attack(model, tokenizer, attack_module, max_tokens=512):
    prompt = getattr(attack_module, 'PROMPT', 'Default prompt')
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=0.7,
            pad_token_id=tokenizer.eos_token_id
        )
    
    response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    success_keywords = getattr(attack_module, 'SUCCESS_KEYWORDS', [])
    success = any(kw.lower() in response.lower() for kw in success_keywords)
    return AttackResult(
        attack_id=attack_module.__name__,
        prompt=prompt,
        response=response,
        success=success,
        keywords_triggered=[kw for kw in success_keywords if kw.lower() in response.lower()]
    )

def compute_lethality(results: list[AttackResult], total_budget_flops: float) -> float:
    successes = sum(1 for r in results if r.success)
    return (successes / len(results)) * 100 if results else 0.0

def sign_provenance(prov: dict, private_key: bytes) -> dict:
    sk = SigningKey.from_string(private_key, curve=SECP256k1)
    sig = sk.sign(json.dumps(prov, sort_keys=True).encode())
    prov['signature'] = sig.hex()
    return prov

def main():
    parser = argparse.ArgumentParser(description="Run Red Queen swarm.")
    parser.add_argument("--target", required=True, help="HuggingFace model ID")
    parser.add_argument("--budget-flops", type=float, default=1e24, help="Attack budget in FLOPs")
    parser.add_argument("--provenance-json", help="Path to provenance.json")
    args = parser.parse_args()

    prov = None
    if args.provenance_json:
        with open(args.provenance_json) as f:
            prov = json.load(f)
        try:
            Provenance(**prov)
        except ValidationError as e:
            print(f"Invalid provenance: {e}")
            sys.exit(1)

    attacks = load_attacks()
    if not attacks:
        print("No attacks found – add to /attacks/")
        sys.exit(1)

    model, tokenizer, accelerator = load_model(args.target)
    results = []

    for attack in attacks:
        result = run_single_attack(model, tokenizer, attack)
        results.append(result)
        print(f"{result.attack_id}: {'SUCCESS' if result.success else 'FAIL'}")

    lethality = compute_lethality(results, args.budget_flops)
    print(f"\n🚨 LETHALITY SCORE: {lethality:.3f}% 🚨")

    report = {
        "model": args.target,
        "timestamp": datetime.utcnow().isoformat(),
        "lethality": lethality,
        "results": [r.dict() for r in results],
        "total_attacks": len(results)
    }
    if prov:
        report["provenance"] = sign_provenance(prov, b'your_private_key_here')  # Replace with real

    with open("report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Report saved to report.json. Upload to Arweave next.")

if __name__ == "__main__":
    main()
