# scripts/merge_lora.py
"""将 Qwen2.5-7B + LoRA adapter 合并并导出为 GGUF 格式（供 Ollama 部署）"""
import os
import sys
import argparse
from pathlib import Path

def merge_and_export(lora_path: str, output_dir: str, base_model: str = "Qwen/Qwen2.5-7B-Instruct"):
    """
    合并 LoRA adapter 到基础模型，导出 GGUF

    依赖:
        pip install transformers peft accelerate
        pip install llama-cpp-python  # GGUF 转换

    或使用 llama.cpp 的 convert脚本:
        git clone https://github.com/ggerganov/llama.cpp
        cd llama.cpp && make
        python convert_hf_to_gguf.py merged_model --outfile merged_model.gguf
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    import torch

    print(f"[1/4] 加载基础模型: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        dtype=torch.float16,
    )

    print(f"[2/4] 加载 LoRA adapter: {lora_path}")
    model = PeftModel.from_pretrained(model, lora_path)

    print("[3/4] 合并 LoRA 权重到基础模型")
    model = model.merge_and_unload()

    merged_path = os.path.join(output_dir, "merged_model")
    os.makedirs(merged_path, exist_ok=True)

    print(f"[3.5/4] 保存合并后的 HF 模型: {merged_path}")
    model.save_pretrained(merged_path, safe_serialization=True)
    tokenizer.save_pretrained(merged_path)

    print("[4/4] 合并完成！")
    print(f"\n下一步：转换为 GGUF 格式")
    print(f"  cd llama.cpp")
    print(f"  python convert_hf_to_gguf.py {merged_path} --outfile {output_dir}/nurbs_expert.gguf")
    print(f"  --quantize q4_k_m (可选量化)")
    print(f"\n然后更新 Modelfile:")
    print(f"  FROM ./{output_dir}/nurbs_expert.gguf")
    print(f"  ollama create nurbs-expert-finetuned -f scripts/Modelfile")

    return merged_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="合并 LoRA adapter 并导出 GGUF")
    parser.add_argument("--lora", default="data/training/nurbs-qwen-lora",
                        help="LoRA adapter 路径")
    parser.add_argument("--output", default="data/training/merged",
                        help="输出目录")
    parser.add_argument("--base", default="Qwen/Qwen2.5-7B-Instruct",
                        help="基础模型名")
    args = parser.parse_args()

    merge_and_export(args.lora, args.output, args.base)
