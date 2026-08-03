"""
Streamlit dashboard – AI provider health monitoring.
OpenRouter-only architecture with model fallback ladder and health tracking.
"""

import streamlit as st
from datetime import datetime
from automation import FinolAutomation

# Human-readable labels for each provider slot
SLOT_LABELS = {
    "openrouter": "OpenRouter",
}

SLOT_ICONS = {
    "openrouter": "🤖",
}

FREE_MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "openai/gpt-oss-20b:free",
    "inclusionai/ling-3.0-flash:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "google/gemma-4-31b-it:free",
]


def _slot_icon(name: str) -> str:
    for prefix, icon in SLOT_ICONS.items():
        if name.startswith(prefix):
            return icon
    return "🔌"


def show_model_selector(default_model: str = None) -> str:
    """Model selection widget. Persists the choice in session_state so it
    drives draft generation regardless of which tab is active."""
    options = list(FREE_MODELS)
    idx = 0
    if default_model and default_model in options:
        idx = options.index(default_model)
    elif st.session_state.get("selected_model") in options:
        idx = options.index(st.session_state["selected_model"])

    selected = st.selectbox(
        "Select AI Model",
        options,
        index=idx,
        help="The AI model used for generating new drafts. Falls back to the next model automatically on rate limits.",
    )
    st.session_state["selected_model"] = selected
    return selected


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
    st.markdown("**Provider Order:**")
    order_parts = []
    for slot in ["openrouter"]:
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
    models = list(FREE_MODELS)
    idx = models.index(default_model) if default_model in models else 0
    return st.selectbox("Select Model", models, index=idx)


def show_fallback_info():
    """Sidebar expander explaining the OpenRouter fallback system."""
    with st.expander("ℹ️ About AI Provider"):
        rows = "".join(f"| {i} | `{m}` | {'Primary' if i == 1 else 'Fallback'} |\n"
                       for i, m in enumerate(FREE_MODELS, 1))
        st.markdown(f"""
### OpenRouter

**Single provider with a free-model fallback ladder:**

| # | Model | Notes |
|---|-------|-------|
{rows}
**What triggers a model switch:**
- API 5xx errors (retried with exponential backoff)
- Free-tier rate limiting (429)
- Model unavailable / removed from the free catalog

**Free models only:**
All models are `:free`-suffixed and verified to work with this key.
If all free models fail, check `OPENROUTER_API_KEY` in Secrets.
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
