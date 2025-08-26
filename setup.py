#!/usr/bin/env python3
"""
Environment Setup for LLM SEO
Quick setup script to prepare the environment for testing
"""

import os
import subprocess
import sys


def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 7):
        print("Python 3.7+ required")
        return False
    print(
        f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                       check=True, capture_output=True)
        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        print("Try: pip install -r requirements.txt")
        return False


def setup_env_file():
    """Setup .env file if it doesn't exist"""
    if os.path.exists(".env"):
        print(".env file already exists")
        return True

    if os.path.exists(".env.example"):
        print("Creating .env from .env.example...")
        with open(".env.example", "r") as src, open(".env", "w") as dst:
            content = src.read()
            dst.write(content)

        print("Please edit .env file and add your API keys:")
        print("   - OPENAI_API_KEY (required for OpenAI provider)")
        return True
    else:
        print("Creating basic .env file...")
        with open(".env", "w") as f:
            f.write("# Add your API keys here\n")
            f.write("OPENAI_API_KEY=your_openai_api_key_here\n")
            f.write("# ANTHROPIC_API_KEY=your_anthropic_key_here\n")

        print("Please edit .env file and add your API keys")
        return True


def check_baml_client():
    """Check if BAML client is properly generated"""
    if os.path.exists("baml_client") and os.path.exists("baml_client/__init__.py"):
        print("BAML client found")
        return True
    else:
        print("BAML client not found")
        print("Run: baml-cli generate")
        return False


def main():
    print("LLM SEO Environment Setup")
    print("=" * 40)

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", install_dependencies),
        ("Environment File", setup_env_file),
        ("BAML Client", check_baml_client),
    ]

    all_passed = True
    for check_name, check_func in checks:
        print(f"\n {check_name}...")
        if not check_func():
            all_passed = False

    print(f"\n{'='*40}")
    if all_passed:
        print("Environment setup complete!")
        print("\nNext steps:")
        print("  1. Edit .env file with your API keys")
        print("  2. python test_suite.py  # Run tests")
        print("  3. python foundamental.py run  # Start analysis")
    else:
        print("Some setup steps failed. Please address the issues above.")

    return all_passed


if __name__ == "__main__":
    main()
