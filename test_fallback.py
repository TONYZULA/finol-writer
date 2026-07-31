"""
Test script to verify the OpenRouter provider fallback system.
Run this to ensure your provider is configured correctly.
"""

import os
import sys
import json
from provider_manager import ProviderManager, FREE_OR_MODELS


class _FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.exceptions.HTTPError(
                f"{self.status_code} Client Error", response=self
            )

    def json(self):
        return self._payload


def test_openrouter_uses_bearer_and_chat_endpoint():
    """Verify OpenRouter calls hit the chat endpoint with Bearer auth."""
    manager = ProviderManager({"OPENROUTER_API_KEY": "test-key"})
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append({"url": url, "json": json, "headers": headers})
        return _FakeResponse(200, {
            "choices": [{"message": {"content": "ok"}}]
        })

    import provider_manager as provider_module

    original_post = provider_module.requests.post
    provider_module.requests.post = fake_post
    try:
        response = manager._call_openrouter(
            manager.providers[0],
            "You are helpful.",
            "hello",
            "google/gemma-4-26b-a4b-it:free",
            json_mode=False,
        )
    finally:
        provider_module.requests.post = original_post

    assert response == "ok"
    assert calls[0]["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert calls[0]["json"]["model"] == "google/gemma-4-26b-a4b-it:free"
    assert calls[0]["json"]["messages"][0]["content"] == "You are helpful."


def test_openrouter_json_mode_sets_response_format():
    """JSON mode should add response_format to the payload."""
    manager = ProviderManager({"OPENROUTER_API_KEY": "test-key"})
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append(json)
        return _FakeResponse(200, {
            "choices": [{"message": {"content": '{"ok": true}'}}]
        })

    import provider_manager as provider_module

    original_post = provider_module.requests.post
    provider_module.requests.post = fake_post
    try:
        response = manager._call_openrouter(
            manager.providers[0], "sys", "user", FREE_OR_MODELS[0], json_mode=True
        )
    finally:
        provider_module.requests.post = original_post

    assert response == '{"ok": true}'
    assert calls[0]["response_format"] == {"type": "json_object"}


def test_ai_call_falls_back_to_next_model_on_failure():
    """A failed model should roll to the next ladder entry."""
    manager = ProviderManager({"OPENROUTER_API_KEY": "test-key"})
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append(json["model"])
        if len(calls) == 1:
            return _FakeResponse(404, text="unavailable for free")
        return _FakeResponse(200, {"choices": [{"message": {"content": "fallback ok"}}]})

    import provider_manager as provider_module

    original_post = provider_module.requests.post
    provider_module.requests.post = fake_post
    try:
        response = manager.ai_call(
            system_prompt="sys",
            user_prompt="hi",
            preferred_model="google/gemma-4-26b-a4b-it:free",
            json_mode=False,
        )
    finally:
        provider_module.requests.post = original_post

    assert response == "fallback ok"
    assert calls[0] == "google/gemma-4-26b-a4b-it:free"
    assert calls[1] == FREE_OR_MODELS[1]

    history = manager.get_call_history(limit=10)
    statuses = [h["status"] for h in history]
    assert statuses[0] == "failed"
    assert statuses[1] == "success"


def test_ai_call_skips_invalid_preferred_model():
    """Legacy Bytez ids (Qwen/...) should be ignored in the ladder."""
    manager = ProviderManager({"OPENROUTER_API_KEY": "test-key"})
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append(json["model"])
        return _FakeResponse(200, {"choices": [{"message": {"content": "ok"}}]})

    import provider_manager as provider_module

    original_post = provider_module.requests.post
    provider_module.requests.post = fake_post
    try:
        manager.ai_call(
            system_prompt="sys",
            user_prompt="hi",
            preferred_model="Qwen/Qwen3-4B",
            json_mode=False,
        )
    finally:
        provider_module.requests.post = original_post

    assert calls[0] == FREE_OR_MODELS[0]


def test_all_models_fail_raises():
    """When every model fails, ai_call should raise a clear error."""
    manager = ProviderManager({"OPENROUTER_API_KEY": "test-key"})

    def fake_post(url, json, headers, timeout):
        return _FakeResponse(500, text="boom")

    import provider_manager as provider_module

    original_post = provider_module.requests.post
    provider_module.requests.post = fake_post
    try:
        try:
            manager.ai_call("sys", "hi", json_mode=False)
        except RuntimeError as e:
            assert "All OpenRouter models failed" in str(e)
        else:
            raise AssertionError("Expected RuntimeError")
    finally:
        provider_module.requests.post = original_post


def test_provider_configuration():
    """Test that the provider is configured correctly."""
    print("=" * 60)
    print("TESTING PROVIDER CONFIGURATION")
    print("=" * 60)

    secrets = {
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
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
            json_mode=True,
        )

        print("\n✅ AI call successful!")
        print(f"Response: {str(response)[:200]}...")

        history = manager.get_call_history(limit=1)
        if history:
            print(f"Model used: {history[-1].get('model', history[-1]['provider'])}")

        return True

    except Exception as e:
        print(f"\n❌ AI call failed: {e}")
        return False


def test_fallback_mechanism(manager: ProviderManager):
    """Test that fallback works when the preferred model fails."""
    print("\n" + "=" * 60)
    print("TESTING FALLBACK MECHANISM")
    print("=" * 60)

    print("\nAttempting call with an unavailable model...")
    print("(This should fallback to other ladder models if first one fails)")

    try:
        response = manager.ai_call(
            system_prompt="You are a helpful assistant.",
            user_prompt="What is 2+2? Answer in one word.",
            preferred_model="google/gemma-4-31b-it:free",
            json_mode=False,
        )

        print("\n✅ Fallback mechanism working!")
        print(f"Response: {str(response)[:100]}")

        history = manager.get_call_history(limit=5)
        print("\nCall history (last 5):")
        for i, call in enumerate(reversed(history), 1):
            status_icon = "✅" if call["status"] == "success" else "❌"
            print(f"  {i}. {status_icon} {call['provider'].upper()} - {call['status']} ({call.get('model')})")

        return True

    except Exception as e:
        print(f"\n❌ All models failed: {e}")
        return False


def test_json_mode_fallback(manager: ProviderManager):
    """Test that JSON mode works."""
    print("\n" + "=" * 60)
    print("TESTING JSON MODE")
    print("=" * 60)

    try:
        response = manager.ai_call(
            system_prompt="You are a helpful assistant. Always respond in valid JSON.",
            user_prompt='Return JSON with field "number" set to 42.',
            json_mode=True,
        )

        print("\n✅ JSON mode working!")
        print(f"Response: {response}")

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
    print("OPENROUTER FALLBACK SYSTEM TEST SUITE")
    print("=" * 60)

    results = {}

    try:
        manager = test_provider_configuration()
        results["Configuration"] = True

        results["Simple Call"] = test_simple_call(manager)
        results["Fallback Mechanism"] = test_fallback_mechanism(manager)
        results["JSON Mode"] = test_json_mode_fallback(manager)
        results["Health Tracking"] = test_provider_health_tracking(manager)

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False

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
    print("\nMake sure you have set the following environment variable:")
    print("  - OPENROUTER_API_KEY (required)")
    print("\nAt least one provider must be configured.\n")

    # Unit tests (no network)
    test_openrouter_uses_bearer_and_chat_endpoint()
    test_openrouter_json_mode_sets_response_format()
    test_ai_call_falls_back_to_next_model_on_failure()
    test_ai_call_skips_invalid_preferred_model()
    test_all_models_fail_raises()
    print("✅ Unit tests passed")

    success = run_all_tests()
    sys.exit(0 if success else 1)
