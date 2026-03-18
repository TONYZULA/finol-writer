"""
Test script to verify multi-provider fallback system.
Run this to ensure your providers are configured correctly.
"""

import os
import sys
from provider_manager import ProviderManager


def test_provider_configuration():
    """Test that providers are configured correctly."""
    print("=" * 60)
    print("TESTING PROVIDER CONFIGURATION")
    print("=" * 60)
    
    # Simulate secrets (in production, these come from st.secrets)
    secrets = {
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", ""),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
        "BYTEZ_API_KEY": os.getenv("BYTEZ_API_KEY", "444d1ac0a8b038cbe61ff956a8cdd700"),
        "OPENROUTER_API_BASE": os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
        "OR_SITE_URL": os.getenv("OR_SITE_URL", ""),
        "OR_APP_NAME": os.getenv("OR_APP_NAME", ""),
    }
    
    manager = ProviderManager(secrets)
    
    print("\n✓ Provider Manager initialized")
    print(f"✓ Available providers: {', '.join(manager.get_available_providers())}")
    
    status = manager.get_provider_status()
    print("\nProvider Status:")
    for provider, info in status.items():
        status_icon = "✅" if info["available"] else "❌"
        print(f"  {status_icon} {provider.upper()}: {'Available' if info['available'] else 'Not configured'}")
    
    return manager


def test_simple_call(manager: ProviderManager):
    """Test a simple AI call with fallback."""
    print("\n" + "=" * 60)
    print("TESTING SIMPLE AI CALL")
    print("=" * 60)
    
    try:
        response = manager.ai_call(
            system_prompt="You are a helpful assistant. Respond in JSON format with a 'message' field.",
            user_prompt="Say hello in one sentence.",
            preferred_model="google/gemini-2.5-flash",
            json_mode=True,
        )
        
        print("\n✅ AI call successful!")
        print(f"Response: {response[:200]}...")
        
        # Show which provider was used
        history = manager.get_call_history(limit=1)
        if history:
            print(f"Provider used: {history[-1]['provider'].upper()}")
        
        return True
    
    except Exception as e:
        print(f"\n❌ AI call failed: {e}")
        return False


def test_fallback_mechanism(manager: ProviderManager):
    """Test that fallback works when preferred provider fails."""
    print("\n" + "=" * 60)
    print("TESTING FALLBACK MECHANISM")
    print("=" * 60)
    
    print("\nAttempting call with potentially unavailable model...")
    print("(This should fallback to other providers if first one fails)")
    
    try:
        response = manager.ai_call(
            system_prompt="You are a helpful assistant.",
            user_prompt="What is 2+2? Answer in one word.",
            preferred_model="google/gemini-2.5-pro",  # May not be available
            json_mode=False,
        )
        
        print("\n✅ Fallback mechanism working!")
        print(f"Response: {response[:100]}")
        
        # Show call history to see fallback attempts
        history = manager.get_call_history(limit=5)
        print("\nCall history (last 5):")
        for i, call in enumerate(reversed(history), 1):
            status_icon = "✅" if call["status"] == "success" else "❌"
            print(f"  {i}. {status_icon} {call['provider'].upper()} - {call['status']}")
        
        return True
    
    except Exception as e:
        print(f"\n❌ All providers failed: {e}")
        return False


def test_bytez_direct(manager: ProviderManager):
    """Test Bytez API directly."""
    print("\n" + "=" * 60)
    print("TESTING BYTEZ API DIRECTLY")
    print("=" * 60)
    
    if "bytez" not in manager.get_available_providers():
        print("\n⚠️  Bytez not configured, skipping test")
        return None
    
    try:
        response = manager.ai_call(
            system_prompt="You are a helpful assistant.",
            user_prompt="Name one color. Just the color name, nothing else.",
            preferred_model="bytez",
            json_mode=False,
        )
        
        print("\n✅ Bytez API working!")
        print(f"Response: {response[:100]}")
        return True
    
    except Exception as e:
        print(f"\n❌ Bytez API failed: {e}")
        return False


def test_json_mode_fallback(manager: ProviderManager):
    """Test that JSON mode fallback works."""
    print("\n" + "=" * 60)
    print("TESTING JSON MODE FALLBACK")
    print("=" * 60)
    
    try:
        response = manager.ai_call(
            system_prompt="You are a helpful assistant. Always respond in valid JSON.",
            user_prompt='Return JSON with field "number" set to 42.',
            json_mode=True,
        )
        
        print("\n✅ JSON mode working!")
        print(f"Response: {response}")
        
        # Verify it's valid JSON
        import json
        if isinstance(response, str):
            json.loads(response)
        
        return True
    
    except Exception as e:
        print(f"\n❌ JSON mode test failed: {e}")
        return False


def test_provider_health_tracking(manager: ProviderManager):
    """Test that provider health is tracked correctly."""
    print("\n" + "=" * 60)
    print("TESTING PROVIDER HEALTH TRACKING")
    print("=" * 60)
    
    status = manager.get_provider_status()
    
    print("\nProvider Health:")
    for provider, info in status.items():
        print(f"\n{provider.upper()}:")
        print(f"  Available: {info['available']}")
        print(f"  Failures: {info['failures']}")
        if info['last_error']:
            print(f"  Last Error: {info['last_error'][:100]}")
    
    return True


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MULTI-PROVIDER FALLBACK SYSTEM TEST SUITE")
    print("=" * 60)
    
    results = {}
    
    try:
        # Test 1: Configuration
        manager = test_provider_configuration()
        results["Configuration"] = True
        
        # Test 2: Simple call
        results["Simple Call"] = test_simple_call(manager)
        
        # Test 3: Fallback mechanism
        results["Fallback Mechanism"] = test_fallback_mechanism(manager)
        
        # Test 4: Bytez direct
        results["Bytez Direct"] = test_bytez_direct(manager)
        
        # Test 5: JSON mode fallback
        results["JSON Mode"] = test_json_mode_fallback(manager)
        
        # Test 6: Health tracking
        results["Health Tracking"] = test_provider_health_tracking(manager)
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        if result is None:
            icon = "⚠️ "
            status = "SKIPPED"
        elif result:
            icon = "✅"
            status = "PASSED"
        else:
            icon = "❌"
            status = "FAILED"
        
        print(f"{icon} {test_name}: {status}")
    
    passed = sum(1 for r in results.values() if r is True)
    total = len([r for r in results.values() if r is not None])
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your fallback system is working correctly.")
        return True
    else:
        print("\n⚠️  Some tests failed. Check configuration and API keys.")
        return False


if __name__ == "__main__":
    print("\nMake sure you have set the following environment variables:")
    print("  - GOOGLE_API_KEY (optional)")
    print("  - OPENROUTER_API_KEY (optional)")
    print("  - BYTEZ_API_KEY (defaults to free tier key)")
    print("\nAt least one provider must be configured.\n")
    
    success = run_all_tests()
    sys.exit(0 if success else 1)
