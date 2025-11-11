#!/usr/bin/env python3
"""
Convert Phi-2 model to GGUF format for local Mac development.

This script:
1. Downloads Phi-2 from Hugging Face (if not already present)
2. Converts to GGUF format using llama.cpp
3. Quantizes to Q4_K_M (4-bit) for mobile/edge devices
"""

import os
import subprocess
import sys

# -----------------------------
# Configuration
# -----------------------------
PROJECT_ROOT = "/Users/mattcho/AndroidStudioProjects/RealitySkin"
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
PHI2_HF_DIR = os.path.join(MODELS_DIR, "phi-2")  # Hugging Face format
PHI2_GGUF_DIR = os.path.join(MODELS_DIR, "phi-2-gguf")  # GGUF output

# llama.cpp paths
LLAMA_CPP_DIR = os.path.join(PROJECT_ROOT, "llama.cpp")
CONVERT_SCRIPT = os.path.join(LLAMA_CPP_DIR, "convert_hf_to_gguf.py")
QUANTIZE_BIN = os.path.join(LLAMA_CPP_DIR, "build", "bin", "llama-quantize")

# Output files
GGUF_FP16_PATH = os.path.join(PHI2_GGUF_DIR, "phi-2-f16.gguf")
GGUF_Q4_PATH = os.path.join(PHI2_GGUF_DIR, "phi-2-q4_k_m.gguf")

# Hugging Face model name
PHI2_MODEL_NAME = "microsoft/phi-2"


# -----------------------------
# Helper Functions
# -----------------------------
def ensure_dir(path):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def run_command(cmd, description):
    """Run shell command and handle errors."""
    print(f"\n{'='*60}")
    print(f"[INFO] {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print(f"\n✅ {description} - COMPLETE")
        return result
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} - FAILED")
        print(f"Error: {e}")
        sys.exit(1)


def check_prerequisites():
    """Verify all required tools are available."""
    print("\n[INFO] Checking prerequisites...")

    # Check llama.cpp
    if not os.path.exists(LLAMA_CPP_DIR):
        print(f"❌ llama.cpp not found at {LLAMA_CPP_DIR}")
        print("Please clone llama.cpp first:")
        print(f"  cd {PROJECT_ROOT} && git clone https://github.com/ggerganov/llama.cpp.git")
        sys.exit(1)

    # Check convert script
    if not os.path.exists(CONVERT_SCRIPT):
        print(f"❌ Conversion script not found: {CONVERT_SCRIPT}")
        sys.exit(1)

    # Check quantize binary
    if not os.path.exists(QUANTIZE_BIN):
        print(f"❌ Quantize binary not found: {QUANTIZE_BIN}")
        print("Please build llama.cpp first:")
        print(f"  cd {LLAMA_CPP_DIR} && cmake -B build && cmake --build build --config Release")
        sys.exit(1)

    # Check Python packages
    try:
        import transformers
        import torch
        import gguf
    except ImportError as e:
        print(f"❌ Missing Python package: {e}")
        print("Install required packages:")
        print("  pip install transformers torch gguf sentencepiece")
        sys.exit(1)

    print("✅ All prerequisites met!\n")


def download_phi2():
    """Download Phi-2 from Hugging Face if not already present."""
    if os.path.exists(PHI2_HF_DIR) and len(os.listdir(PHI2_HF_DIR)) > 0:
        print(f"[INFO] Phi-2 already downloaded at {PHI2_HF_DIR}")
        return

    print(f"[INFO] Downloading Phi-2 from Hugging Face...")
    ensure_dir(PHI2_HF_DIR)

    # Use Hugging Face CLI or Python API
    try:
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=PHI2_MODEL_NAME,
            local_dir=PHI2_HF_DIR,
            local_dir_use_symlinks=False
        )
        print(f"✅ Phi-2 downloaded to {PHI2_HF_DIR}")
    except Exception as e:
        print(f"❌ Failed to download Phi-2: {e}")
        print("\nManual download instructions:")
        print(f"1. Visit: https://huggingface.co/{PHI2_MODEL_NAME}")
        print(f"2. Download model files to: {PHI2_HF_DIR}")
        sys.exit(1)


def convert_to_gguf():
    """Convert Hugging Face model to GGUF format."""
    ensure_dir(PHI2_GGUF_DIR)

    cmd = [
        sys.executable,  # Use current Python interpreter
        CONVERT_SCRIPT,
        PHI2_HF_DIR,
        "--outfile", GGUF_FP16_PATH,
        "--outtype", "f16"  # 16-bit floating point (no quantization yet)
    ]

    run_command(cmd, "Converting Phi-2 to GGUF (FP16)")


def quantize_gguf():
    """Quantize GGUF model to 4-bit Q4_K_M."""
    cmd = [
        QUANTIZE_BIN,
        GGUF_FP16_PATH,
        GGUF_Q4_PATH,
        "Q4_K_M"  # 4-bit quantization, medium quality
    ]

    run_command(cmd, "Quantizing to Q4_K_M (4-bit)")


def print_summary():
    """Print final summary with file sizes."""
    print("\n" + "="*60)
    print("🎉 CONVERSION COMPLETE!")
    print("="*60)

    if os.path.exists(GGUF_FP16_PATH):
        fp16_size = os.path.getsize(GGUF_FP16_PATH) / (1024**3)  # GB
        print(f"\n📦 FP16 Model (full precision):")
        print(f"   Path: {GGUF_FP16_PATH}")
        print(f"   Size: {fp16_size:.2f} GB")

    if os.path.exists(GGUF_Q4_PATH):
        q4_size = os.path.getsize(GGUF_Q4_PATH) / (1024**3)  # GB
        print(f"\n📦 Q4_K_M Model (quantized, recommended for mobile):")
        print(f"   Path: {GGUF_Q4_PATH}")
        print(f"   Size: {q4_size:.2f} GB")

    print("\n💡 Next Steps:")
    print("   1. Test the model with llama.cpp:")
    print(f"      {LLAMA_CPP_DIR}/build/bin/llama-cli -m {GGUF_Q4_PATH} -p 'Hello, I am'")
    print("\n   2. Copy Q4 model to Android app assets for on-device inference")
    print()


# -----------------------------
# Main Pipeline
# -----------------------------
def main():
    print("="*60)
    print("Phi-2 to GGUF Conversion Pipeline")
    print("="*60)

    # Step 1: Check prerequisites
    check_prerequisites()

    # Step 2: Download Phi-2 (if needed)
    download_phi2()

    # Step 3: Convert to GGUF
    convert_to_gguf()

    # Step 4: Quantize to Q4_K_M
    quantize_gguf()

    # Step 5: Print summary
    print_summary()


if __name__ == "__main__":
    main()
