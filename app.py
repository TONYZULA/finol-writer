import streamlit as st
from automation import FinolAutomation

st.set_page_config(page_title="FINOL AI Writer", layout="wide")

# Persistent state for the manual edit box
if 'draft' not in st.session_state: st.session_state.draft = ""

with st.sidebar:
    st.title("Settings")
    model = st.selectbox("AI Model", ["google/gemini-1.5-pro", "openrouter/x-ai/grok-2"])
    
    # Secure key inputs
    g_key = st.text_input("Google Key", type="password")
    t_key = st.text_input("Tavily Key", type="password")
    temp_key = st.text_input("Templated Key", type="password")
    
    st.markdown("---")
    wp_url = st.text_input("WP URL (https://...)")
    wp_user = st.text_input("WP Username")
    wp_pass = st.text_input("WP App Password", type="password")

st.title("🚀 FINOL Blog Writer")

# Step 1: Input
with st.expander("Article Details", expanded=not st.session_state.draft):
    topic = st.text_input("Topic")
    audience = st.text_input("Audience")
    goal = st.text_area("Goal")
    target = st.number_input("Word Target", value=1000)
    
    if st.button("Generate Draft"):
        keys = {"GOOGLE_API_KEY": g_key, "TAVILY_API_KEY": t_key}
        agent = FinolAutomation(model, keys)
        with st.spinner("Writing..."):
            st.session_state.draft = agent.run_writing_pipeline(topic, audience, goal, target)
            st.rerun()

# Step 2: Edit & Publish
if st.session_state.draft:
    st.subheader("Edit Content")
    edited_text = st.text_area("Final Polish", value=st.session_state.draft, height=400)
    st.session_state.draft = edited_text # Save edits

    if st.button("✅ Publish to WordPress"):
        keys = {"GOOGLE_API_KEY": g_key, "TAVILY_API_KEY": t_key, "TEMPLATED_API_KEY": temp_key}
        wp_config = {"url": wp_url, "user": wp_user, "pass": wp_pass}
        agent = FinolAutomation(model, keys)
        
        with st.spinner("Uploading Media & Post..."):
            img = agent.generate_cover_image(topic)
            link = agent.upload_to_wordpress(topic, edited_text, img, wp_config)
            st.success(f"Published: {link}")
