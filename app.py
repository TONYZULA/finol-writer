import streamlit as st
from automation import FinolAutomation
from provider_dashboard import (
    show_provider_status,
    show_call_history,
    show_provider_selector,
    show_fallback_info,
    show_debug_panel,
)

st.set_page_config(page_title="FINOL AI Writer", layout="wide")

if 'draft' not in st.session_state: 
    st.session_state.draft = ""
if 'agent' not in st.session_state:
    st.session_state.agent = None

with st.sidebar:
    st.title("⚙️ Settings")
    
    # Provider and model selection
    model = st.selectbox("Select AI Model", [
        "google/gemini-2.5-pro",
        "google/gemini-2.5-flash",
        "openrouter/arcee-ai/trinity-large-preview:free",
        "openrouter/arcee-ai/trinity-mini:free",
        "openrouter/cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        "openrouter/google/gemma-3-12b-it:free",
        "openrouter/google/gemma-3-27b-it:free",
        "openrouter/google/gemma-3-4b-it:free",
        "openrouter/google/gemma-3n-e2b-it:free",
        "openrouter/google/gemma-3n-e4b-it:free",
        "openrouter/liquid/lfm-2.5-1.2b-instruct:free",
        "openrouter/liquid/lfm-2.5-1.2b-thinking:free",
        "openrouter/meta-llama/llama-3.2-3b-instruct:free",
        "openrouter/meta-llama/llama-3.3-70b-instruct:free",
        "openrouter/minimax/minimax-m2.5:free",
        "openrouter/mistralai/mistral-small-3.1-24b-instruct:free",
        "openrouter/nousresearch/hermes-3-llama-3.1-405b:free",
        "openrouter/nvidia/nemotron-3-nano-30b-a3b:free",
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
        "openrouter/nvidia/nemotron-nano-12b-v2-vl:free",
        "openrouter/nvidia/nemotron-nano-9b-v2:free",
        "openrouter/openai/gpt-oss-120b:free",
        "openrouter/openai/gpt-oss-20b:free",
        "openrouter/openrouter/free",
        "openrouter/qwen/qwen3-4b:free",
        "openrouter/qwen/qwen3-coder:free",
        "openrouter/qwen/qwen3-next-80b-a3b-instruct:free",
        "openrouter/stepfun/step-3.5-flash:free",
        "openrouter/z-ai/glm-4.5-air:free"
    ])
    
    st.markdown("---")
    st.subheader("WordPress Credentials")
    wp_url = st.text_input("WP URL (https://...)")
    wp_user = st.text_input("WP Username")
    wp_pass = st.text_input("WP App Password", type="password")
    
    st.markdown("---")
    show_fallback_info()

st.title("🚀 FINOL Blog Writer")

# Tabs for main content and monitoring
tab1, tab2, tab3 = st.tabs(["✍️ Write Article", "📊 Provider Monitor", "🔧 Debug"])

with tab1:
    with st.expander("Article Details", expanded=not st.session_state.draft):
        topic = st.text_input("Topic")
        audience = st.text_input("Audience")
        goal = st.text_area("Goal")
        target = st.number_input("Word Target", value=1000)
        
        if st.button("Generate Draft"):
            agent = FinolAutomation(model)
            st.session_state.agent = agent
            with st.spinner("Writing..."):
                try:
                    st.session_state.draft = agent.run_writing_pipeline(topic, audience, goal, target)
                    st.rerun()
                except Exception as e:
                    st.error("Draft generation failed.")
                    st.info(
                        "Common fixes (Streamlit Cloud):\n"
                        "- Add `TAVILY_API_KEY`\n"
                        "- If using `openrouter/...` models: add `OPENROUTER_API_KEY`\n"
                        "- If using `google/gemini-...` models: add `GOOGLE_API_KEY`\n"
                        "- If using Bytez models: add `BYTEZ_API_KEY`\n"
                        "- If OpenRouter is blocked in your environment: set `OPENROUTER_API_BASE`\n"
                    )
                    st.exception(e)

    if st.session_state.draft:
        st.subheader("Edit Content")
        edited_text = st.text_area("Final Polish (Markdown)", value=st.session_state.draft, height=400)
        st.session_state.draft = edited_text 

        if st.button("✅ Publish to WordPress"):
            # Validate WordPress credentials
            if not wp_url or not wp_user or not wp_pass:
                st.error("Please fill in all WordPress credentials (URL, Username, App Password)")
            else:
                wp_config = {"url": wp_url, "user": wp_user, "pass": wp_pass}
                agent = FinolAutomation(model)
                st.session_state.agent = agent
                with st.spinner("Uploading Media & Post..."):
                    try:
                        img = agent.generate_cover_image(topic)
                        link = agent.upload_to_wordpress(topic, edited_text, img, wp_config)
                        st.success(f"Published successfully! [View Post]({link})")
                    except Exception as e:
                        st.error("Publishing failed.")
                        st.info(
                            "Common WordPress issues:\n"
                            "- Verify WordPress URL is correct (include https://)\n"
                            "- Use Application Password, not regular password\n"
                            "- Check WordPress REST API is enabled\n"
                            "- Verify user has publishing permissions\n"
                            "- Check WordPress site is accessible\n\n"
                            "To create Application Password:\n"
                            "WordPress Admin → Users → Profile → Application Passwords"
                        )
                        st.exception(e)

with tab2:
    if st.session_state.agent:
        show_provider_status(st.session_state.agent)
        st.divider()
        show_call_history(st.session_state.agent)
    else:
        st.info("Generate a draft first to see provider statistics")

with tab3:
    if st.session_state.agent:
        show_debug_panel(st.session_state.agent)
    else:
        st.info("Generate a draft first to see debug information")