"""
Hugging Face Spaces 1-Click Deployment Script for Valura AI
============================================================
This script deploys the Valura AI multi-agent service directly to Hugging Face Spaces.

Requirements:
  pip install huggingface_hub

Usage:
  python deploy_hf.py --repo-id <YOUR_USERNAME>/valura-ai-dashboard --token <YOUR_HF_TOKEN>
"""

import os
import sys
import argparse

# Fix Windows console encoding for emoji-free output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(description="Deploy Valura AI to Hugging Face Spaces")
    parser.add_argument("--repo-id", required=False, help="Space repo ID (e.g. username/valura-ai-dashboard)")
    parser.add_argument("--token", required=False, help="Hugging Face User Access Token")
    args = parser.parse_args()

    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        print("[*] Installing huggingface_hub...")
        os.system(f"{sys.executable} -m pip install huggingface_hub")
        from huggingface_hub import HfApi, create_repo

    repo_id = args.repo_id or os.getenv("HF_SPACE_ID")
    token = args.token or os.getenv("HF_TOKEN")

    if not repo_id:
        repo_id = input("Enter your Hugging Face Space ID (e.g. your-username/valura-ai): ").strip()
    if not token:
        token = input("Enter your Hugging Face Access Token (Write permissions): ").strip()

    if not repo_id or not token:
        print("[ERROR] repo_id and token are required.")
        sys.exit(1)

    api = HfApi(token=token)

    print(f"\n[DEPLOY] Creating/Verifying Hugging Face Space: {repo_id} (Docker SDK)...")
    try:
        create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            private=False,
            token=token,
            exist_ok=True
        )
        print("[OK] Space repository ready.")
    except Exception as e:
        print(f"[NOTICE] {e}")

    print("\n[UPLOAD] Uploading project files to Hugging Face Space...")
    ignore_patterns = [
        ".git",
        ".git/*",
        ".github/*",
        "__pycache__",
        "__pycache__/*",
        "*.pyc",
        ".env",
        "runs/*",
        ".agents/*",
        "deploy_hf.py",
    ]

    try:
        api.upload_folder(
            folder_path=".",
            repo_id=repo_id,
            repo_type="space",
            ignore_patterns=ignore_patterns,
            token=token,
        )
        print(f"\n[SUCCESS] Deployed successfully!")
        print(f"[LINK] Live Space URL: https://huggingface.co/spaces/{repo_id}")
        print("[INFO] The Space will automatically build the Docker container and start up.")
        print("[INFO] It may take 2-5 minutes for the first build.")
    except Exception as e:
        print(f"\n[ERROR] Deployment error: {e}")
        print("\nAlternative Git deployment method:")
        print(f"  git remote add space https://huggingface.co/spaces/{repo_id}")
        print(f"  git push space main:main")


if __name__ == "__main__":
    main()
