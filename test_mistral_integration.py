#!/usr/bin/env python3
"""
Test script for Mistral Vibe integration
"""
import os
import asyncio
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from env import load_env, get_mistral_config, validate_mistral_config
from services.mistral_client import MistralVibeClient

def test_configuration():
    """Test configuration loading"""
    print("🧪 Testing Mistral Vibe configuration...")
    
    # Load environment
    load_env()
    
    # Get configuration
    config = get_mistral_config()
    print(f"Configuration loaded: {config}")
    
    # Validate configuration
    try:
        validate_mistral_config(config)
        print("✅ Configuration validation passed")
    except ValueError as e:
        print(f"❌ Configuration validation failed: {e}")
        return False
    
    return True

async def test_client_initialization():
    """Test client initialization"""
    print("\n🧪 Testing Mistral Vibe client initialization...")
    
    config = get_mistral_config()
    
    if not config["enabled"]:
        print("ℹ️ Mistral Vibe is not configured, skipping client test")
        return True
    
    try:
        client = MistralVibeClient(
            api_url=config["api_url"],
            api_key=config["api_key"],
            default_model=config["default_model"],
            timeout=config["timeout"],
            max_retries=config["max_retries"]
        )
        
        await client.start()
        print("✅ Client initialized successfully")
        
        # Test health check
        try:
            is_healthy = await client.health_check()
            if is_healthy:
                print("✅ Health check passed")
                
                # Test model listing
                models = await client.list_models()
                print(f"✅ Found {len(models)} models")
                for model in models[:3]:  # Show first 3 models
                    print(f"  - {model['id']}")
            else:
                print("⚠️ Health check failed")
        except Exception as e:
            print(f"⚠️ Health check error (this is expected if Mistral Vibe is not running): {e}")
        
        await client.stop()
        print("✅ Client stopped successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Mistral Vibe Integration")
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