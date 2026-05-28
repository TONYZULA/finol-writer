"""
Streamlit dashboard – AI provider health monitoring.
Reflects the new rolling-fallback architecture:
  AIML (×3) → OpenRouter FREE (×3) → Gemini (×2)
"""

import streamlit as st
from datetime import datetime
from automation import FinolAutomation

# Human-readable labels for each provider slot
SLOT_LABELS = {
    "aiml_1":        "AIML API – Key 1 (auto)",
    "aiml_2":        "AIML API – Key 2 (muli)",
    "aiml_3":        "AIML API – Key 3 (harsi)",
    "openrouter_1":  "OpenRouter – Key 1 [FREE only]",
    "openrouter_2":  "OpenRouter – Key 2 [FREE only]",
    "openrouter_3":  "OpenRouter – Key 3 [FREE only]",
    "gemini_1":      "Gemini – Key 1",
    "gemini_2":      "Gemini – Key 2",
}

SLOT_ICONS = {
    "aiml":       "🤖",
    "openrouter": "🔀",
    "gemini":     "✨",
}


def _slot_icon(name: str) -> str:
    for prefix, icon in SLOT_ICONS.items():
        if name.startswith(prefix):
            return icon
    return "🔌"


def show_provider_status(agent: FinolAutomation):
    """Display provider health status."""
    st.subheader("🔄 Provider Status")

    status    = agent.provider_manager.get_provider_status()
    available = agent.provider_manager.get_available_providers()

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active Slots", len(available))
    with col2:
        total_failures = sum(v["failures"] for v in status.values())
        st.metric("Total Failures", total_failures)
    with col3:
        st.metric("Configured Slots", len(status))

    # Fallback order diagram
    st.markdown("**Fallback Order:**")
    order_parts = []
    for slot in ["aiml_1", "aiml_2", "aiml_3",
                 "openrouter_1", "openrouter_2", "openrouter_3",
                 "gemini_1", "gemini_2"]:
        if slot in status:
            icon  = _slot_icon(slot)
            avail = "✅" if status[slot]["available"] else "❌"
            order_parts.append(f"{avail} {icon} {SLOT_LABELS.get(slot, slot)}")
    st.markdown("  →  ".join(order_parts) if order_parts else "_No providers configured_")

    st.divider()

    # Per-slot detail
    st.markdown("**Slot Details:**")
    for slot_name, info in status.items():
        label = SLOT_LABELS.get(slot_name, slot_name.upper())
        icon  = _slot_icon(slot_name)
        badge = "✅ Available" if info["available"] else "❌ Unavailable"

        with st.expander(f"{icon} {label}  —  {badge}"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Status**: {badge}")
                st.write(f"**Failures**: {info['failures']}")
            with c2:
                if info["last_error"]:
                    st.write(f"**Last Error**: {info['last_error'][:120]}")
                if info["last_error_time"]:
                    t = datetime.fromtimestamp(info["last_error_time"])
                    st.write(f"**Error Time**: {t.strftime('%Y-%m-%d %H:%M:%S')}")


def show_call_history(agent: FinolAutomation, limit: int = 20):
    """Display recent API call history."""
    st.subheader("📋 Call History")

    history = agent.provider_manager.get_call_history(limit=limit)

    if not history:
        st.info("No calls made yet.")
        return

    successful  = sum(1 for h in history if h["status"] == "success")
    failed      = sum(1 for h in history if h["status"] == "failed")
    auth_failed = sum(1 for h in history if h["status"] == "auth_failed")

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Successful", successful)
    with c2: st.metric("Failed",     failed)
    with c3: st.metric("Auth Errors", auth_failed)

    st.markdown("**Recent Calls:**")
    for i, call in enumerate(reversed(history), 1):
        ts   = datetime.fromtimestamp(call["timestamp"])
        icon = "✅" if call["status"] == "success" else "❌"
        slot = call["provider"]
        label = SLOT_LABELS.get(slot, slot.upper())

        with st.expander(
            f"{icon} {i}. {label}  —  {call['status']}  ({ts.strftime('%H:%M:%S')})"
        ):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Slot**: {label}")
                st.write(f"**Status**: {call['status']}")
            with c2:
                st.write(f"**Time**: {ts.strftime('%Y-%m-%d %H:%M:%S')}")
                if "model" in call:
                    st.write(f"**Model**: `{call['model']}`")
            if "error" in call:
                st.error(f"**Error**: {call['error']}")


def show_provider_selector(default_model: str = None):
    """Standalone model selector widget (used externally if needed)."""
    models = [
        "google/gemini-2.0-flash",
        "google/gemini-2.5-flash",
        "openrouter/google/gemma-3-27b-it:free",
        "openrouter/meta-llama/llama-3.3-70b-instruct:free",
        "openrouter/mistralai/mistral-small-3.1-24b-instruct:free",
    ]
    idx = models.index(default_model) if default_model in models else 0
    return st.selectbox("Select Model", models, index=idx)


def show_fallback_info():
    """Sidebar expander explaining the fallback system."""
    with st.expander("ℹ️ About Fallback System"):
        st.markdown("""
### Rolling Multi-Provider Fallback

**Provider order (8 independent slots):**

| # | Provider | Notes |
|---|----------|-------|
| 1 | 🤖 AIML API – Key 1 | Primary |
| 2 | 🤖 AIML API – Key 2 | Fallback |
| 3 | 🤖 AIML API – Key 3 | Fallback |
| 4 | 🔀 OpenRouter – Key 1 | **FREE models only** |
| 5 | 🔀 OpenRouter – Key 2 | **FREE models only** |
| 6 | 🔀 OpenRouter – Key 3 | **FREE models only** |
| 7 | ✨ Gemini – Key 1 | Fallback |
| 8 | ✨ Gemini – Key 2 | Last resort |

**What triggers a slot switch:**
- Rate limit exceeded
- API connection error
- Timeout (>60 s)
- Authentication failure (disables slot permanently)

**OpenRouter free-model enforcement:**
All OpenRouter calls are forced to `:free` models regardless of what is selected in the dropdown.
        """)


def show_debug_panel(agent: FinolAutomation):
    """Debug panel with provider stats."""
    with st.expander("🔧 Debug Panel"):
        available = agent.provider_manager.get_available_providers()
        st.write(f"**Active slots**: {', '.join(available) or 'None'}")

        st.markdown("**Recent Errors:**")
        status    = agent.provider_manager.get_provider_status()
        has_error = False
        for slot, info in status.items():
            if info["last_error"]:
                label = SLOT_LABELS.get(slot, slot)
                st.warning(f"**{label}**: {info['last_error']}")
                has_error = True
        if not has_error:
            st.success("No recent errors.")

        st.markdown("**Call Statistics:**")
        history = agent.provider_manager.get_call_history(limit=200)
        if history:
            stats: dict = {}
            for call in history:
                p = call["provider"]
                stats.setdefault(p, {"success": 0, "failed": 0})
                if call["status"] == "success":
                    stats[p]["success"] += 1
                else:
                    stats[p]["failed"] += 1

            for slot, s in stats.items():
                total   = s["success"] + s["failed"]
                rate    = (s["success"] / total * 100) if total else 0
                label   = SLOT_LABELS.get(slot, slot)
                st.write(f"**{label}**: {s['success']}/{total} ({rate:.0f}% success)")
        else:
            st.info("No call history yet.")
