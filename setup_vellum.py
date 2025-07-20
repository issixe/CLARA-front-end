#!/usr/bin/env python3
"""
Vellum Setup Script for CLARA Fitness Reports
Hackathon Configuration Helper
"""

import os
import json
from pathlib import Path

def setup_vellum():
    """Setup Vellum API configuration for the hackathon."""
    
    print("🏆 CLARA Fitness Reports - Vellum Integration Setup")
    print("=" * 50)
    print()
    
    # Check if .env file exists
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ Found existing .env file")
        with open(env_file, "r") as f:
            existing_content = f.read()
    else:
        existing_content = ""
        print("📝 Creating new .env file")
    
    # Get Vellum API credentials
    print("\n🔑 Vellum API Configuration")
    print("-" * 30)
    
    vellum_api_key = input("Enter your Vellum API Key: ").strip()
    
    if not vellum_api_key:
        print("❌ Vellum API Key is required!")
        return False
    
    # Create or update .env file
    env_content = existing_content
    
    # Add or update Vellum configuration
    if "VELLUM_API_KEY" in env_content:
        # Update existing
        lines = env_content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith("VELLUM_API_KEY="):
                lines[i] = f"VELLUM_API_KEY={vellum_api_key}"
                break
        env_content = '\n'.join(lines)
    else:
        # Add new
        if env_content and not env_content.endswith('\n'):
            env_content += '\n'
        env_content += f"VELLUM_API_KEY={vellum_api_key}\n"
    
    # Write .env file
    with open(env_file, "w") as f:
        f.write(env_content)
    
    print(f"✅ Vellum API Key saved to {env_file}")
    
    # Create a test script
    test_script = """#!/usr/bin/env python3
\"\"\"
Test Vellum Integration
Run this to verify your Vellum setup is working
\"\"\"

import os
import vellum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_vellum():
    api_key = os.getenv("VELLUM_API_KEY")
    
    if not api_key:
        print("❌ VELLUM_API_KEY not found in environment variables")
        return False
    
    try:
        # Initialize Vellum client
        client = vellum.Vellum(api_key=api_key)
        
        # Test with a simple prompt
        response = client.generate(
            model="gpt-4",
            prompt="Say 'Hello from Vellum!' and nothing else.",
            max_tokens=50,
            temperature=0.1
        )
        
        print("✅ Vellum API connection successful!")
        print(f"Response: {response.choices[0].text.strip()}")
        return True
        
    except Exception as e:
        print(f"❌ Vellum API test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_vellum()
"""
    
    with open("test_vellum.py", "w") as f:
        f.write(test_script)
    
    print("✅ Created test_vellum.py for API testing")
    
    # Instructions
    print("\n📋 Next Steps:")
    print("1. Install python-dotenv: pip install python-dotenv")
    print("2. Test your setup: python test_vellum.py")
    print("3. Start the Flask server: flask run")
    print("4. Generate a fitness report in the CLARA app")
    print()
    print("🎯 For the hackathon:")
    print("- Make sure to mention Vellum integration in your demo")
    print("- Show how AI-generated insights improve user experience")
    print("- Highlight the fallback system for reliability")
    
    return True

if __name__ == "__main__":
    setup_vellum() 