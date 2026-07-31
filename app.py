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
    
    # Model selection – OpenRouter free models (verified working)
    model = st.selectbox("Select AI Model", [
        "google/gemma-4-26b-a4b-it:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "openai/gpt-oss-20b:free",
        "inclusionai/ling-3.0-flash:free",
        "nvidia/nemotron-nano-9b-v2:free",
    ])
    
    st.markdown("---")
    st.subheader("WordPress Credentials")
    wp_url = st.text_input("WP URL (https://...)")
    wp_user = st.text_input("WP Username")
    wp_pass = st.text_input("WP App Password", type="password")
    
    st.markdown("---")
    show_fallback_info()

    st.markdown("---")
    st.subheader("Cover Image")
    cover_image = st.file_uploader(
        "Upload Featured Image",
        type=["jpg", "jpeg", "png", "webp"],
        help="Optional. This image will be uploaded as the WordPress featured image.",
        key="cover_image_upload",
    )
    if cover_image:
        st.image(cover_image, caption=cover_image.name, use_column_width=True)
    else:
        st.info("No cover image selected. Publishing will continue without a featured image.")

st.title("🚀 FINOL Blog Writer")

# Tabs for main content and monitoring
tab1, tab2, tab3 = st.tabs(["✍️ Write Article", "📊 Provider Monitor", "🔧 Debug"])

with tab1:
    with st.expander("Article Details", expanded=not st.session_state.draft):
        topic = st.text_input("Topic")
        audience = st.text_input("Audience")
        goal = st.text_area("Goal")
        target = st.number_input("Word Target", value=1000)
        
        # Knowledge Base / Pillar Links for Internal Linking
        knowledge_input = st.text_area(
            "Pillar / Internal Links (Optional)",
            placeholder=(
                "Anchor Text: URL\n"
                "best branding agency in Ahmedabad: https://pandavaz.com/best-branding-agency-in-ahmedabad/\n"
                "logo design trends in Ahmedabad: https://pandavaz.com/logo-design-ahmedabad-2026-trends/\n"
                "social media marketing for your brand: https://pandavaz.com/the-best-social-media-agency-in-ahmedabad-for-2026/"
            ),
            help=(
                "One link per line. Format: 'Exact Anchor Text: https://your-url'\n"
                "The AI will use your exact phrase as the clickable hyperlink text in the blog.\n"
                "Bare URLs are also accepted — title is auto-generated from the URL slug."
            ),
            height=140,
        )
        
        # Parse knowledge base — supports both "Title: URL" and bare URL formats
        def _url_to_title(url: str) -> str:
            """Auto-generate a readable title from a URL slug."""
            try:
                from urllib.parse import urlparse
                path = urlparse(url).path.rstrip('/')
                slug = path.split('/')[-1] if path else ''
                return slug.replace('-', ' ').replace('_', ' ').title() or url
            except Exception:
                return url

        knowledge_base = []
        if knowledge_input:
            for raw_line in knowledge_input.split('\n'):
                line = raw_line.strip()
                if not line:
                    continue
                # Bare URL: line starts with http:// or https://
                if line.startswith('http://') or line.startswith('https://'):
                    knowledge_base.append({"title": _url_to_title(line), "url": line})
                elif ':' in line:
                    # "Title: URL" format — split on FIRST colon only
                    title, url = line.split(':', 1)
                    url = url.strip()
                    # Re-attach the protocol if the URL got split (e.g. "Title:https://...")
                    if url.startswith('//') or not url.startswith('http'):
                        # It's a relative path or the split ate 'https'
                        pass
                    knowledge_base.append({"title": title.strip(), "url": url})

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
                        "- Add `OPENROUTER_API_KEY`\n"
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
                        img = cover_image.getvalue() if cover_image else None
                        image_name = cover_image.name if cover_image else None
                        image_type = cover_image.type if cover_image else None
                        link = agent.upload_to_wordpress(
                            topic,
                            edited_text,
                            img,
                            wp_config,
                            image_filename=image_name,
                            image_content_type=image_type,
                        )
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
