#!/usr/bin/env python3
"""
Test script for Mistral Vibe integration with configuration
"""
import os
import asyncio
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set test environment
os.environ['ENV_FILE'] = os.path.join(os.path.dirname(__file__), '.env.test')

from env import load_env, get_mistral_config, validate_mistral_config
from services.mistral_client import MistralVibeClient

def test_configuration():
    """Test configuration loading"""
    print("🧪 Testing Mistral Vibe configuration with test config...")
    
    # Load environment
    load_env()
    
    # Get configuration
    config = get_mistral_config()
    print(f"Configuration loaded: {config}")
    
    # Validate configuration
    try:
        validate_mistral_config(config)
        print("✅ Configuration validation passed")
        return True
    except ValueError as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

async def test_client_initialization():
    """Test client initialization"""
    print("\n🧪 Testing Mistral Vibe client initialization...")
    
    config = get_mistral_config()
    
    if not config["enabled"]:
        print("ℹ️ Mistral Vibe is not configured")
        return False
    
    try:
        client = MistralVibeClient(
            api_url=config["api_url"],
            api_key=config["api_key"],
            default_model=config["default_model"],
            timeout=config["timeout"],
            max_retries=config["max_retries"]
        )
        
        print(f"✅ Client created with config: {config}")
        
        await client.start()
        print("✅ Client session started")
        
        # Test health check (this will likely fail since we don't have a real Mistral Vibe server)
        try:
            is_healthy = await client.health_check()
            if is_healthy:
                print("✅ Health check passed")
            else:
                print("⚠️ Health check failed (expected for test setup)")
        except Exception as e:
            print(f"⚠️ Health check error (expected for test setup): {type(e).__name__}")
        
        await client.stop()
        print("✅ Client stopped successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Client test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Mistral Vibe Integration with Config")
    print("=" * 50)
    
    # Test configuration
    config_ok = test_configuration()
    
    # Test client (async)
    if config_ok:
        client_ok = asyncio.run(test_client_initialization())
    else:
        client_ok = False
    
    print("\n" + "=" * 50)
    if config_ok and client_ok:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())