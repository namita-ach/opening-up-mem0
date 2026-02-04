#!/usr/bin/env python3
"""
Setup Verification Script for Mem0 LOCOMO Benchmarking
Checks all required dependencies and configuration
"""

import os
import sys
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    print("Checking Python version...")
    version = sys.version_info
    print(f"   Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("Python 3.9+ required")
        return False
    print("Python version OK")
    return True


def check_dependencies():
    """Check if all required packages are installed."""
    print("\nChecking required packages...")
    
    required_packages = {
        'mem0': 'mem0ai',
        'openai': 'openai',
        'dotenv': 'python-dotenv',
        'jinja2': 'jinja2',
        'nltk': 'nltk',
        'tqdm': 'tqdm',
        'numpy': 'numpy',
        'sklearn': 'scikit-learn',
    }
    
    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"{package}")
        except ImportError:
            print(f"{package} (missing)")
            missing.append(package)
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print(f"\nInstall with:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True


def check_nltk_data():
    """Check if required NLTK data is downloaded."""
    print("\nChecking NLTK data...")
    try:
        import nltk
        try:
            nltk.data.find('tokenizers/punkt')
            print("punkt tokenizer")
        except LookupError:
            print("Downloading punkt...")
            nltk.download('punkt', quiet=True)
        
        try:
            nltk.data.find('corpora/wordnet')
            print("wordnet")
        except LookupError:
            print("Downloading wordnet...")
            nltk.download('wordnet', quiet=True)
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def check_env_file():
    """Check if .env file exists and has required keys."""
    print("\nChecking environment configuration...")
    
    env_path = Path(".env")
    if not env_path.exists():
        print(".env file not found")
        print("\nCreate .env file")
        return False
    
    print(".env file exists")
    
    # Check for required keys
    required_keys = ['OPENAI_API_KEY', 'MEM0_API_KEY', 'MEM0_PROJECT_ID', 'MEM0_ORGANIZATION_ID']
    
    from dotenv import dotenv_values
    config = dotenv_values(".env")
    
    missing_keys = []
    placeholder_keys = []
    
    for key in required_keys:
        if key not in config or not config[key]:
            missing_keys.append(key)
            print(f"{key} (missing)")
        elif config[key].startswith("your-"):
            placeholder_keys.append(key)
            print(f"{key} (needs to be set)")
        else:
            # Mask the key for security
            masked_value = config[key][:8] + "..." if len(config[key]) > 8 else "***"
            print(f"{key} ({masked_value})")
    
    if missing_keys or placeholder_keys:
        print("\nPlease configure all API keys in .env file")
        return False
    
    return True


def check_dataset():
    """Check if LOCOMO dataset exists."""
    print("\nChecking dataset...")
    
    dataset_path = Path("dataset/locomo10.json")
    if not dataset_path.exists():
        print(f"{dataset_path} not found")
        return False
    
    print(f"{dataset_path}")
    
    # Check file size
    size_mb = dataset_path.stat().st_size / (1024 * 1024)
    print(f"Size: {size_mb:.2f} MB")
    
    return True


def check_results_dir():
    """Check if results directory exists."""
    print("\nChecking results directory...")
    
    results_dir = Path("results")
    if not results_dir.exists():
        print("Creating results/ directory...")
        results_dir.mkdir(exist_ok=True)
    
    print("results/ directory ready")
    return True


def test_mem0_connection():
    """Test connection to Mem0 API."""
    print("\nTesting Mem0 API connection...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from mem0 import MemoryClient
        
        client = MemoryClient(
            api_key=os.getenv("MEM0_API_KEY"),
            org_id=os.getenv("MEM0_ORGANIZATION_ID"),
            project_id=os.getenv("MEM0_PROJECT_ID"),
        )
        
        print("Mem0 API connection successful")
        return True
        
    except Exception as e:
        print(f"Mem0 API error: {e}")
        print("\nCheck your Mem0 credentials in .env file")
        return False


def test_openai_connection():
    """Test connection to OpenAI API."""
    print("\nTesting OpenAI API connection...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from openai import OpenAI
        
        client = OpenAI()
        
        # Try a simple API call
        response = client.models.list()
        print("OpenAI API connection successful")
        return True
        
    except Exception as e:
        print(f"OpenAI API error: {e}")
        print("\nCheck your OPENAI_API_KEY in .env file")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("  Mem0 LOCOMO Benchmark - Setup Verification")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("NLTK Data", check_nltk_data),
        ("Environment File", check_env_file),
        ("Dataset", check_dataset),
        ("Results Directory", check_results_dir),
    ]
    
    # Run basic checks
    results = []
    for name, check_func in checks:
        result = check_func()
        results.append(result)
    
    # Only test API connections if env file is properly configured
    if results[3]:  # env file check passed
        api_checks = [
            ("OpenAI Connection", test_openai_connection),
            ("Mem0 Connection", test_mem0_connection),
        ]
        
        for name, check_func in api_checks:
            result = check_func()
            results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    if all(results):
        print("All checks passed! You're ready to run benchmarks.")
        print("\nQuick start:")
        print("   ./run_mem0_benchmark.sh quick    # Quick test")
        print("   ./run_mem0_benchmark.sh full     # Full benchmark")
        print("   ./run_mem0_benchmark.sh help     # See all options")
    else:
        print("Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("   1. Install missing packages: pip install -r requirements.txt")
        print("   2. Create .env file: cp .env.example .env")
        print("   3. Configure API keys in .env file")
        sys.exit(1)
    
    print("=" * 60)


if __name__ == "__main__":
    main()
