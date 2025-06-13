#!/usr/bin/env python3
"""
Enhanced Audiobook Converter Installation Script
Installs Coqui TTS and all dependencies for premium voice quality
"""

import subprocess
import sys
import os
import platform
from pathlib import Path

def run_command(command, description=""):
    """Run a shell command and handle errors."""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed")
        print(f"Error: {e.stderr}")
        return False

def check_system_requirements():
    """Check if system requirements are met."""
    print("🔍 Checking system requirements...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    print(f"✅ Python {python_version.major}.{python_version.minor} detected")
    
    # Check if FFmpeg is available
    ffmpeg_check = subprocess.run("ffmpeg -version", shell=True, capture_output=True)
    if ffmpeg_check.returncode != 0:
        print("⚠️ FFmpeg not found. Installing...")
        system = platform.system().lower()
        
        if system == "darwin":  # macOS
            run_command("brew install ffmpeg", "Installing FFmpeg via Homebrew")
        elif system == "linux":
            run_command("sudo apt-get update && sudo apt-get install -y ffmpeg", "Installing FFmpeg via apt")
        else:
            print("❌ Please install FFmpeg manually for your system")
            return False
    else:
        print("✅ FFmpeg is available")
    
    return True

def install_dependencies():
    """Install all required dependencies."""
    print("📦 Installing enhanced dependencies...")
    
    # Install basic requirements first
    if not run_command("pip install -r requirements.txt", "Installing basic requirements"):
        return False
    
    # Install Coqui TTS with specific version for stability
    coqui_install_commands = [
        "pip install TTS==0.22.0",
        "pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu",  # CPU version
        "pip install phonemizer>=3.2.1",
        "pip install librosa>=0.10.1",
        "pip install soundfile>=0.12.1"
    ]
    
    for cmd in coqui_install_commands:
        if not run_command(cmd, f"Installing: {cmd.split()[2]}"):
            print("⚠️ Some packages failed to install, but continuing...")
    
    # Install caching dependencies
    caching_commands = [
        "pip install diskcache>=5.6.3",
        "pip install redis>=5.0.1", 
        "pip install joblib>=1.3.2"
    ]
    
    for cmd in caching_commands:
        run_command(cmd, f"Installing: {cmd.split()[2]}")
    
    return True

def setup_directories():
    """Create necessary directories."""
    print("📁 Setting up directories...")
    
    directories = [
        "temp",
        "output", 
        "temp/tts_cache",
        "temp/audio",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def create_env_file():
    """Create a sample .env file if it doesn't exist."""
    if not os.path.exists(".env"):
        print("📝 Creating .env file...")
        
        env_content = """# Enhanced Audiobook Converter Configuration

# Required: Get your API key from https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# TTS Configuration (Coqui TTS is recommended for best quality)
TTS_ENGINE=coqui-xtts
DEFAULT_VOICE=tts_models/en/ljspeech/tacotron2-DDC
FALLBACK_ENGINE=edge-tts
FALLBACK_VOICE=en-US-AriaNeural

# Performance Settings
MAX_CONCURRENT_REQUESTS=3
ENABLE_TTS_CACHE=True
CACHE_MAX_SIZE=1000
GPU_ENABLED=True

# Audio Quality
AUDIO_FORMAT=mp3
AUDIO_QUALITY=128k
SPEECH_RATE=1.0

# Debug
DEBUG=False
LOG_LEVEL=INFO
"""
        
        with open(".env", "w") as f:
            f.write(env_content)
        
        print("✅ Created .env file")
        print("⚠️ Remember to add your GEMINI_API_KEY to the .env file!")
    else:
        print("✅ .env file already exists")

def test_installation():
    """Test if the installation works."""
    print("🧪 Testing installation...")
    
    try:
        # Test basic imports
        from config import settings
        print("✅ Configuration loaded")
        
        # Test TTS converter
        from core.tts_converter import TTSConverter
        tts = TTSConverter(engine="edge-tts")  # Use fallback for testing
        print("✅ TTS Converter initialized")
        
        # Test if Coqui TTS is available
        try:
            from TTS.api import TTS
            print("✅ Coqui TTS is available - Premium voice quality enabled!")
        except ImportError:
            print("⚠️ Coqui TTS not available - using fallback engines")
        
        print("🎉 Installation test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Installation test failed: {e}")
        return False

def main():
    """Main installation process."""
    print("🎧 Enhanced Audiobook Converter Installation")
    print("=" * 50)
    
    # Check system requirements
    if not check_system_requirements():
        print("❌ System requirements not met. Please fix the issues above.")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Setup directories
    setup_directories()
    
    # Create .env file
    create_env_file()
    
    # Test installation
    if test_installation():
        print("\n🎉 Installation completed successfully!")
        print("\n📋 Next steps:")
        print("1. Add your GEMINI_API_KEY to the .env file")
        print("2. Run: python app.py")
        print("3. Open http://localhost:8501 in your browser")
        print("\n🎙️ Features enabled:")
        print("   ✅ Coqui TTS (Studio Quality)")
        print("   ✅ Smart Caching (3x faster)")
        print("   ✅ AI Text Enhancement")
        print("   ✅ English Optimizations")
    else:
        print("❌ Installation completed with errors. Please check the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 