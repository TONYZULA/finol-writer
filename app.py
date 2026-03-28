import streamlit as st
import os
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
    model = st.selectbox("Select AI Model (Bytez)", [
        "google/gemini-2.5-pro",
        "google/gemini-2.5-flash",
        "google/gemini-2.5-flash-lite",
        "openai/gpt-4o-mini",
        "anthropic/claude-sonnet-4-5",
        "Qwen/Qwen3-4B",
        "meta-llama/Llama-2-7b-chat-hf",
    ])
    
    st.markdown("---")
    st.subheader("WordPress Credentials")
    wp_url = st.text_input("WP URL (https://...)")
    wp_user = st.text_input("WP Username")
    wp_pass = st.text_input("WP App Password", type="password")
    
    st.markdown("---")
    show_fallback_info()

    st.markdown("---")
    st.subheader("Default Cover Image")
    cover_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "cover.png")
    if os.path.exists(cover_path):
        st.image(cover_path, caption="Default cover used for every post", use_column_width=True)
    else:
        st.warning("Default cover image not found at assets/cover.png")

st.title("🚀 FINOL Blog Writer")

# Tabs for main content and monitoring
tab1, tab2, tab3 = st.tabs(["✍️ Write Article", "📊 Provider Monitor", "🔧 Debug"])

with tab1:
    with st.expander("Article Details", expanded=not st.session_state.draft):
        topic = st.text_input("Topic")
        audience = st.text_input("Audience")
        goal = st.text_area("Goal")
        target = st.number_input("Word Target", value=1000)
        
        # Knowledge Base for Internal Linking
        knowledge_input = st.text_area(
            "Knowledge Base / Core Links (Optional)", 
            placeholder="Title: URL\nServices: https://pandavaz.com/services\nAbout: https://pandavaz.com/about",
            help="Add links to your core pages (Services, Portfolio, etc.) so the AI can link to them naturally."
        )
        
        # Parse knowledge base
        knowledge_base = []
        if knowledge_input:
            lines = knowledge_input.split('\n')
            for line in lines:
                if ':' in line:
                    parts = line.split(':', 1)
                    knowledge_base.append({"title": parts[0].strip(), "url": parts[1].strip()})

        if st.button("Generate Draft"):
            agent = FinolAutomation(model)
            st.session_state.agent = agent
            with st.spinner("Writing..."):
                try:
                    # Pass WP context for internal linking
                    wp_context = {"url": wp_url.strip()} if wp_url else None
                    st.session_state.draft = agent.run_writing_pipeline(
                        topic, audience, goal, target, 
                        wp_config=wp_context,
                        knowledge_base=knowledge_base
                    )
                    st.rerun()
                except Exception as e:
                    st.error("Draft generation failed.")
                    st.info(
                        "Common fixes (Streamlit Cloud):\n"
                        "- Add `TAVILY_API_KEY`\n"
                        "- Add `BYTEZ_API_KEY`\n"
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
                wp_config = {
                    "url": wp_url.strip(), 
                    "user": wp_user.strip(), 
                    "pass": wp_pass.strip()
                }
                agent = FinolAutomation(model)
                st.session_state.agent = agent
                with st.spinner("Uploading Media & Post..."):
                    try:
                        # Upload to WordPress with hardcoded cover image
                        img = agent.get_default_cover_image_bytes()
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
