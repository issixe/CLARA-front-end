#!/usr/bin/env python3
"""
Test Vellum Integration
Run this to verify your Vellum setup is working
"""

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
