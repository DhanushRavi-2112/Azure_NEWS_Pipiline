#!/usr/bin/env python3
"""
Setup script for Azure News Pipeline
"""

import subprocess
import sys
import os

def run_command(command):
    """Run shell command and handle errors"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {command}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {command}")
        print(f"Error: {e.stderr}")
        return None

def setup_environment():
    """Setup Python virtual environment and dependencies"""
    print("🚀 Setting up Azure News Pipeline...")
    
    # Create virtual environment
    if not os.path.exists("clean_venv"):
        print("📦 Creating virtual environment...")
        run_command("python -m venv clean_venv")
    
    # Install dependencies
    print("📥 Installing dependencies...")
    if sys.platform == "win32":
        pip_path = "clean_venv\\Scripts\\pip.exe"
        python_path = "clean_venv\\Scripts\\python.exe"
    else:
        pip_path = "clean_venv/bin/pip"
        python_path = "clean_venv/bin/python"
    
    run_command(f"{pip_path} install --upgrade pip")
    run_command(f"{pip_path} install -r requirements.txt")
    
    # Download spaCy model
    print("🔤 Downloading spaCy English model...")
    run_command(f"{python_path} -m spacy download en_core_web_sm")
    
    print("\n✅ Setup complete!")
    print("\n📋 Next steps:")
    print("1. Setup PostgreSQL database")
    print("2. Start Miniflux: docker-compose -f docker-compose-miniflux.yml up -d")
    print("3. Start Stage-A: cd Stage-A_Microservice && docker-compose up -d")
    print("4. Start pipeline: cd miniflux_news_pipeline/app && python filtered_pipeline.py")

if __name__ == "__main__":
    setup_environment()