"""
Streamlit dashboard component for monitoring AI provider health and fallback system.
"""

import streamlit as st
from datetime import datetime
from automation import FinolAutomation


def show_provider_status(agent: FinolAutomation):
    """Display provider health status in Streamlit."""
    st.subheader("🔄 Provider Status")
    
    status = agent.provider_manager.get_provider_status()
    available = agent.provider_manager.get_available_providers()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Available Providers", len(available))
    
    with col2:
        total_failures = sum(p["failures"] for p in status.values())
        st.metric("Total Failures", total_failures)
    
    with col3:
        st.metric("Configured Providers", len(status))
    
    # Detailed provider info
    st.write("**Provider Details:**")
    for provider_name, info in status.items():
        with st.expander(f"📊 {provider_name.upper()}"):
            col1, col2 = st.columns(2)
            
            with col1:
                status_badge = "✅ Available" if info["available"] else "❌ Unavailable"
                st.write(f"**Status**: {status_badge}")
                st.write(f"**Failures**: {info['failures']}")
            
            with col2:
                if info["last_error"]:
                    st.write(f"**Last Error**: {info['last_error'][:100]}...")
                if info["last_error_time"]:
                    error_time = datetime.fromtimestamp(info["last_error_time"])
                    st.write(f"**Error Time**: {error_time.strftime('%Y-%m-%d %H:%M:%S')}")


def show_call_history(agent: FinolAutomation, limit: int = 20):
    """Display recent API call history."""
    st.subheader("📋 Call History")
    
    history = agent.provider_manager.get_call_history(limit=limit)
    
    if not history:
        st.info("No calls made yet")
        return
    
    # Summary stats
    col1, col2, col3 = st.columns(3)
    
    successful = sum(1 for h in history if h["status"] == "success")
    failed = sum(1 for h in history if h["status"] == "failed")
    auth_failed = sum(1 for h in history if h["status"] == "auth_failed")
    
    with col1:
        st.metric("Successful", successful)
    with col2:
        st.metric("Failed", failed)
    with col3:
        st.metric("Auth Errors", auth_failed)
    
    # Detailed history table
    st.write("**Recent Calls:**")
    
    for i, call in enumerate(reversed(history), 1):
        timestamp = datetime.fromtimestamp(call["timestamp"])
        status_icon = "✅" if call["status"] == "success" else "❌"
        
        with st.expander(
            f"{status_icon} {i}. {call['provider'].upper()} - {call['status']} "
            f"({timestamp.strftime('%H:%M:%S')})"
        ):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Provider**: {call['provider']}")
                st.write(f"**Status**: {call['status']}")
            
            with col2:
                st.write(f"**Time**: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                if "model" in call:
                    st.write(f"**Model**: {call['model']}")
            
            if "error" in call:
                st.error(f"**Error**: {call['error']}")


def show_provider_selector(default_model: str = None):
    """Display provider and model selector."""
    st.subheader("🤖 AI Provider & Model Selection")
    
    models = [
        "google/gemini-2.5-pro",
        "google/gemini-2.5-flash",
        "google/gemini-2.5-flash-lite",
        "openai/gpt-4o-mini",
        "anthropic/claude-sonnet-4-5",
        "Qwen/Qwen3-4B",
        "meta-llama/Llama-2-7b-chat-hf",
    ]
    
    selected_model = st.selectbox(
        "Select Model",
        models,
        index=0 if not default_model else (models.index(default_model) if default_model in models else 0),
    )
    
    return selected_model


def show_fallback_info():
    """Display information about the fallback system."""
    with st.expander("ℹ️ About Fallback System"):
        st.markdown("""
        ### Bytez-Only Provider

        The app is configured to use Bytez exclusively (no Gemini/OpenRouter).

        **What triggers retries:**
        - API connection errors
        - Rate limit exceeded
        - Request timeouts
        - Authentication failures

        **Retry strategy:**
        - Exponential backoff: 2s → 4s → 8s (max 10s)
        - JSON mode fallback if a model doesn't support it

        **Benefits:**
        - ✅ Simpler setup (single provider)
        - ✅ No cross-provider failures
        - ✅ Provider health tracking

        See `PROVIDER_SETUP.md` for detailed configuration.
        """)


def show_debug_panel(agent: FinolAutomation):
    """Show debug information for troubleshooting."""
    with st.expander("🔧 Debug Panel"):
        st.write("**Provider Configuration:**")
        
        available = agent.provider_manager.get_available_providers()
        st.write(f"Available providers: {', '.join(available)}")
        
        st.write("\n**Recent Errors:**")
        status = agent.provider_manager.get_provider_status()
        
        has_errors = False
        for provider_name, info in status.items():
            if info["last_error"]:
                st.warning(f"**{provider_name}**: {info['last_error']}")
                has_errors = True
        
        if not has_errors:
            st.success("No recent errors")
        
        st.write("\n**Call Statistics:**")
        history = agent.provider_manager.get_call_history(limit=100)
        
        if history:
            provider_stats = {}
            for call in history:
                provider = call["provider"]
                if provider not in provider_stats:
                    provider_stats[provider] = {"success": 0, "failed": 0}
                
                if call["status"] == "success":
                    provider_stats[provider]["success"] += 1
                else:
                    provider_stats[provider]["failed"] += 1
            
            for provider, stats in provider_stats.items():
                total = stats["success"] + stats["failed"]
                success_rate = (stats["success"] / total * 100) if total > 0 else 0
                st.write(
                    f"**{provider}**: {stats['success']}/{total} successful "
                    f"({success_rate:.1f}%)"
                )
