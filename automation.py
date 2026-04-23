import os
import json
import requests
import streamlit as st
import markdown
from typing import List, Dict
from tavily import TavilyClient
from provider_manager import ProviderManager

class FinolAutomation:
    def __init__(self, model):
        self.model = model
        
        # Safe loading from st.secrets to prevent blank screen crashes
        self.keys = {
            "TAVILY_API_KEY": st.secrets.get("TAVILY_API_KEY", ""),
            "BYTEZ_API_KEY": st.secrets.get("BYTEZ_API_KEY", ""),
            "GOOGLE_API_KEY": st.secrets.get("GOOGLE_API_KEY", ""),
            "OPENROUTER_API_KEY": st.secrets.get("OPENROUTER_API_KEY", ""),
        }
        
        # Initialize provider manager for multi-provider fallback
        self.provider_manager = ProviderManager(self.keys)
        
        # Initialization logic
        if not self.keys["TAVILY_API_KEY"]:
            st.error("Missing TAVILY_API_KEY in Streamlit Secrets!")
            self.tavily = None
        else:
            self.tavily = TavilyClient(api_key=self.keys["TAVILY_API_KEY"])

    def fetch_internal_links(self, wp_url):
        """Fetch existing posts to use as internal linking suggestions."""
        try:
            # Standardize URL
            clean_url = str(wp_url).strip().rstrip('/')
            if clean_url.startswith("http://"):
                clean_url = clean_url.replace("http://", "https://", 1)
            
            # Fetch latest 10 posts
            posts_url = f"{clean_url}/wp-json/wp/v2/posts?per_page=10&status=publish"
            res = requests.get(posts_url, timeout=10)
            if res.status_code == 200:
                posts = res.json()
                links = []
                for p in posts:
                    title = p.get('title', {}).get('rendered', '')
                    link = p.get('link', '')
                    if title and link:
                        links.append({"title": title, "url": link})
                return links
        except Exception:
            pass
        return []

    def humanize_and_sanitize(self, text):
        """Remove invisible characters and potential AI-watermark patterns."""
        if not text:
            return ""
        
        # 1. Remove Zero-Width Spaces and invisible control characters (often used as AI signatures)
        invisible_chars = [
            '\u200b', '\u200c', '\u200d', '\ufeff', # Zero-width
            '\u00ad', # Soft hyphen
            '\u2028', '\u2029', # Line/Paragraph separators
        ]
        sanitized = text
        for char in invisible_chars:
            sanitized = sanitized.replace(char, '')
            
        # 2. Basic 'Humanizer' - vary common AI repetitive structures
        # (This is handled primarily via the refined prompt, but we ensure clean ASCII/UTF-8 here)
        return sanitized.strip()

    def ai_call(self, system_prompt, user_prompt, json_mode=True):
        """
        Make AI call with automatic multi-provider fallback.
        Tries preferred model first, then falls back to other providers.
        """
        content = self.provider_manager.ai_call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            preferred_model=self.model,
            json_mode=json_mode,
        )
        
        if json_mode:
            # If content is already a dict, return it
            if isinstance(content, dict):
                return content
            # Otherwise try to parse as JSON
            return self._safe_json_loads(content)
        else:
            return content

    def _safe_json_loads(self, text: str):
        """Safely parse JSON from text, handling various formats."""
        # If already a dict, return it
        if isinstance(text, dict):
            return text
            
        try:
            return json.loads(text)
        except Exception:
            # Attempt to recover JSON object embedded in extra text
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except:
                    pass
            
            # If all JSON parsing fails, return a safe default structure
            # This prevents KeyError when accessing expected fields
            return {"error": "Failed to parse JSON", "raw_content": str(text)}

    def get_default_cover_image_bytes(self):
        """Load the hardcoded cover image from the repo."""
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(base_dir, "assets", "cover.png")
        if not os.path.exists(image_path):
            st.warning("Cover image not found at assets/cover.png. Publishing without featured image.")
            return None
        with open(image_path, "rb") as f:
            return f.read()

    def upload_to_wordpress(self, title, content, image_bytes, wp_config):
        """Upload blog post with cover image to WordPress."""
        # Clean and validate credentials
        user = str(wp_config.get('user', '')).strip()
        password = str(wp_config.get('pass', '')).strip()
        url = str(wp_config.get('url', '')).strip().rstrip('/')
        
        # Force HTTPS for security and to prevent auth loss during redirects
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)
            st.warning("⚠️ Upgraded WordPress URL to HTTPS to ensure secure authentication.")
        
        auth = (user, password)
        base_url = url
        
        # Ensure base_url doesn't have trailing /wp-json
        if base_url.endswith('/wp-json'):
            base_url = base_url[:-8]
        
        media_id = None
        
        # Only try to upload image if we have image bytes
        if image_bytes:
            # Upload media (cover image)
            media_url = f"{base_url}/wp-json/wp/v2/media"
            headers = {
                "Content-Disposition": 'attachment; filename="cover.jpg"',
                "Content-Type": "image/jpeg"
            }
            
            try:
                media_response = requests.post(
                    media_url, 
                    data=image_bytes, 
                    headers=headers, 
                    auth=auth,
                    timeout=30,
                    allow_redirects=False # Prevent auth leak
                )
                
                # Check for success (201 Created)
                if media_response.status_code == 201:
                    media_res = media_response.json()
                    media_id = media_res.get("id")
                    if media_id:
                        st.success(f"✅ Featured image uploaded successfully!")
                else:
                    st.warning(f"Media upload returned {media_response.status_code}. Continuing without featured image.")
                    media_id = None
                    
            except Exception as e:
                # If media upload fails, continue without featured image
                st.warning(f"Cover image upload failed: {str(e)}. Continuing without image.")
                media_id = None
        else:
            st.info("No cover image provided. Publishing without featured image.")
        
        # Convert Markdown to HTML for WordPress
        # uses extensions for better tables, fenced code blocks, etc.
        html_content = markdown.markdown(content, extensions=['fenced_code', 'tables', 'nl2br', 'sane_lists'])
        
        # Create post with HTML content
        post_url = f"{base_url}/wp-json/wp/v2/posts"
        payload = {
            "title": title,
            "content": html_content,
            "status": "publish"
        }
        
        # Add featured media if available
        if media_id:
            payload["featured_media"] = media_id
        
        try:
            # Debug: Show the URL being used
            st.info(f"Publishing to: {post_url}")
            
            post_response = requests.post(
                post_url, 
                json=payload, 
                auth=auth,
                timeout=30,
                allow_redirects=False # Prevent auth leak and silent GET conversion
            )
            
            # Check if response is successful (201 Created)
            if post_response.status_code == 201:
                post_res = post_response.json()
                return post_res.get("link", f"{base_url}/?p={post_res.get('id', 'unknown')}")
            
            # Handle 3xx Redirects
            if 300 <= post_response.status_code < 400:
                location = post_response.headers.get("Location", "unknown")
                raise Exception(
                    f"WordPress redirected the request to: {location}\n"
                    f"This usually happens when using HTTP instead of HTTPS. "
                    f"Please ensure your WordPress URL in settings starts with 'https://'."
                )

            # Some WordPress setups return 200 for posts created via plugins
            if post_response.status_code == 200:
                try:
                    post_res = post_response.json()
                    # If it's a list, it's a GET response (failure)
                    if isinstance(post_res, list):
                        raise Exception("Received a list of posts instead of a single created post. Check if your URL redirected to a GET request.")
                    return post_res.get("link", f"{base_url}/wp-admin/edit.php")
                except:
                    return f"{base_url}/wp-admin/edit.php"
            
            # Handle errors
            error_detail = post_response.text[:500]
            raise Exception(f"Post creation failed: {post_response.status_code} - {error_detail}")
                
        except Exception as e:
            # Provide helpful error message based on error type
            error_msg = str(e)
            if "404" in error_msg and "rest_no_route" in error_msg:
                raise Exception(
                    f"WordPress REST API not found. Please check:\n"
                    f"1. Permalink Settings: Go to Settings → Permalinks → Select 'Post name' → Save\n"
                    f"2. Verify URL is correct: {base_url}\n"
                    f"3. Test REST API: Visit {base_url}/wp-json/wp/v2/posts in browser\n"
                    f"Original error: {error_msg}"
                )
            else:
                raise Exception(f"WordPress publishing failed: {error_msg}")

    def run_writing_pipeline(self, topic, audience, goal, word_target, wp_config=None, knowledge_base=None):
        if not self.tavily:
            return "Error: Research tool not initialized."
        
        # Fetch internal links if WordPress config is available
        internal_links = []
        if wp_config and wp_config.get('url'):
            with st.spinner("Fetching internal links for suggestions..."):
                internal_links = self.fetch_internal_links(wp_config['url'])
        
        # Merge with manual knowledge base links
        all_suggestions = (knowledge_base or []) + internal_links
        links_context = ""
        if all_suggestions:
            links_context = (
                "\n\n=== MANDATORY INTERNAL LINKING RULES ===\n"
                "You MUST embed the following pillar/internal links naturally into the blog content.\n"
                "CRITICAL: Use the EXACT anchor text shown below — word for word. "
                "Do NOT paraphrase, shorten, or reword the anchor text.\n"
                "Each link should appear ONCE, placed where it reads naturally in a sentence.\n\n"
                "Anchor Text → URL (copy the markdown link exactly as shown):\n"
            )
            for link in all_suggestions:
                anchor = link.get('title', '').strip()
                url = link.get('url', '').strip()
                if anchor and url:
                    links_context += f'  • [{anchor}]({url})\n'
            links_context += (
                "\nExample of CORRECT usage:\n"
                '  ✅ "...which is why choosing the [best branding agency in Ahmedabad]'
                '(https://pandavaz.com/best-branding-agency-in-ahmedabad/) matters so much."\n'
                "Example of WRONG usage (anchor text changed — NOT allowed):\n"
                '  ❌ "...choosing the [top agency in Ahmedabad](https://pandavaz.com/...) matters."\n'
                "=== END INTERNAL LINKING RULES ===\n\n"
            )

        # Research phase - Articles
        try:
            search_res = self.tavily.search(query=f"{topic} {audience}", search_depth="advanced", include_images=False)
            urls = [r['url'] for r in search_res.get('results', [])[:5]]
        except Exception:
            urls = []
        
        # No external image embedding to avoid broken/hotlinked images
        images_context = ""

        # SEO phase - Focus on natural keyword integration
        seo_sys = """You are a modern SEO specialist (2026 standards).
        Identify a total of 4-5 keywords that are closely related and natural.
        Avoid keyword stuffing - focus on semantic relevance and user intent.
        Return JSON with:
        - 'primary_keyword': The main focus keyword (1-3 words)
        - 'keywords': A list of 4-5 total keywords including the primary keyword

        Modern SEO prioritizes:
        1. Natural language and readability
        2. Semantic relevance over exact matches
        3. User intent over keyword density
        4. Topic authority over keyword quantity"""
        
        seo_data = self.ai_call(seo_sys, f"Topic: {topic}, Audience: {audience}, Sources: {urls}")
        
        # Handle SEO data parsing errors
        if isinstance(seo_data, dict) and "error" in seo_data:
            seo_data = {
                "primary_keyword": topic,
                "keywords": [topic, audience, "solutions", "strategies", "benefits"]
            }
        elif isinstance(seo_data, dict):
            primary = seo_data.get("primary_keyword", topic)
            raw_keywords = seo_data.get("keywords", [])
            if not isinstance(raw_keywords, list):
                raw_keywords = [str(raw_keywords)]
            # Ensure primary keyword is first and keep 4-5 total unique keywords.
            keywords = [primary] + [k for k in raw_keywords if isinstance(k, str)]
            deduped = []
            for k in keywords:
                k = k.strip()
                if k and k.lower() not in {d.lower() for d in deduped}:
                    deduped.append(k)
            seo_data["primary_keyword"] = primary
            seo_data["keywords"] = deduped[:5]

        # Outline phase - Natural structure
        map_sys = """You are a content strategist creating a natural, engaging blog outline.
        Create sections that flow logically and tell a story.
        Avoid repetitive keyword-heavy titles.
        
        Return JSON with 'sections' array containing objects with:
        - 'title': Natural, engaging section title (NOT keyword-stuffed)
        - 'word_count': Target words for this section
        - 'focus': What this section should accomplish (value for reader)
        
        Good section titles:
        ✅ "Why This Matters Now"
        ✅ "The Real-World Impact"
        ✅ "Getting Started: A Practical Approach"
        
        Bad section titles (avoid):
        ❌ "AI Content Generation for Agencies Benefits"
        ❌ "AI Creator Systems Advertising Solutions"
        ❌ "AI Workflow Ad Agencies Implementation"
        
        Ensure total word count matches target."""
        
        outline = self.ai_call(map_sys, f"Topic: {topic}, Target: {word_target}, Goal: {goal}, Audience: {audience}")
        
        # Handle outline parsing errors
        if isinstance(outline, dict) and "error" in outline:
            # Create a default outline
            outline = {
                "sections": [
                    {"title": "Introduction", "word_count": word_target // 5, "focus": "Hook reader and set context"},
                    {"title": "The Current Landscape", "word_count": word_target // 4, "focus": "Explain the situation"},
                    {"title": "Key Insights and Strategies", "word_count": word_target // 3, "focus": "Provide value"},
                    {"title": "Practical Implementation", "word_count": word_target // 5, "focus": "Actionable steps"},
                    {"title": "Looking Ahead", "word_count": word_target // 10, "focus": "Future perspective"}
                ]
            }
        
        # Ensure sections exist
        if not isinstance(outline, dict) or 'sections' not in outline:
            outline = {
                "sections": [
                    {"title": "Introduction", "word_count": word_target // 5, "focus": "Hook reader"},
                    {"title": "Main Content", "word_count": word_target // 2, "focus": "Core value"},
                    {"title": "Conclusion", "word_count": word_target // 5, "focus": "Wrap up"}
                ]
            }

        # Writing phase - Natural, engaging content
        blog_content = ""
        writer_sys = f"""You are an expert content writer creating engaging, natural blog content.

WRITING PRINCIPLES:
1. Write for HUMANS first. Use an active, personal, and mentored voice.
2. VARY sentence lengths. Use contractions (it's, can't, don't) for a conversational tone.
3. AVOID AI cliches: "In the digital age", "unlock your potential", "discover the secret", etc.
4. BE specific: mention real Ahmedabad references contextually.
5. FORMATting: Use **bold** for emphasis, bullet points for readability, and 2-3 sentence paragraphs.

{links_context if len(all_suggestions) > 3 else ''} # Only keep context here if list is long

Return only the well-written Markdown content for the requested section. Do NOT return JSON."""
        
        for section in outline['sections']:
            section_title = section.get('title', 'Section') if isinstance(section, dict) else str(section)
            section_words = section.get('word_count', 200) if isinstance(section, dict) else 200
            section_focus = section.get('focus', 'Provide value') if isinstance(section, dict) else 'Provide value'
            
            section_input = f"""
WRITING PERMISSION: Write the blog section titled "{section_title}".

SECTION REQUIREMENTS:
- Target Words: {section_words}
- Section Purpose: {section_focus}

{links_context}

SEO KEYWORDS (use 1-2 naturally):
- {', '.join(seo_data.get('keywords', [])[:5])}

ADDITIONAL CONTACT INFO:
- +919879972778 or +919925822542 (mention naturally)
- [Services](https://pandavaz.com/services/) (mention once naturally as a link)

PREVIOUS PROGRESS:
{blog_content[-400:] if blog_content else 'This is the very first section.'}

INSTRUCTION: Write only the content for this specific section. Use headings ONLY if they are sub-headings (###). The main section heading (##) will be added automatically.
"""
            
            try:
                # Use plain text mode for higher reliability with Bytez models
                written = self.ai_call(writer_sys, section_input, json_mode=False)
                
                # CLEANING: Remove the section title if the AI repeated it at the start
                clean_written = str(written).strip()
                # Remove common header prefixes if AI added them
                temp_text = clean_written.lstrip('#').strip()
                
                # If the AI started with the section title, strip it to avoid duplication
                if temp_text.lower().startswith(section_title.lower()):
                    # Find where the title ends and keep the rest
                    clean_written = temp_text[len(section_title):].lstrip(' :-\n\r').strip()
                
                # Ensure we always add the main section header exactly once
                blog_content += f"\n\n## {section_title}\n\n{clean_written}"
                    
            except Exception as e:
                blog_content += f"\n\n## {section_title}\n\n[Content generation failed: {str(e)}]"
            
        # Post-Processing Failsafe:
        # If the AI mentioned our anchor phrases but forgot the link brackets, fix it now.
        blog_content = self._apply_pillar_failsafe(blog_content, all_suggestions)
        
        blog_content = self._auto_link_urls(blog_content)
        blog_content = self._auto_link_phone_numbers(blog_content)
        return self.humanize_and_sanitize(blog_content)

    def _apply_pillar_failsafe(self, text: str, suggestions: List[Dict]) -> str:
        """
        Manually inject links if the AI used the anchor text but omitted the URL.
        Prevents cases where AI ignores markdown formatting instructions.
        """
        if not text or not suggestions:
            return text
            
        import re
        processed = text
        for s in suggestions:
            anchor = s.get('title', '').strip()
            url = s.get('url', '').strip()
            if not anchor or not url:
                continue
            
            # Escape anchor for regex
            safe_anchor = re.escape(anchor)
            
            # Pattern: find the anchor text ONLY if it's NOT already part of a link
            # Match anchor if not preceded by [ or followed by ](
            pattern = re.compile(rf"(?<!\[){safe_anchor}(?!\]\()", re.IGNORECASE)
            
            # Replace occurrences with markdown link
            processed = pattern.sub(f"[{anchor}]({url})", processed)
            
        return processed

    def _auto_link_urls(self, text: str) -> str:
        """Convert bare URLs to markdown links when not already linked."""
        if not text:
            return text

        import re

        def replacer(match: re.Match) -> str:
            url = match.group(0)
            start = match.start()
            # Avoid converting URLs already in markdown links or images.
            if start >= 2 and text[start - 2:start] == "](":
                return url
            if start >= 4 and text[start - 4:start] == "![](":
                return url
            return f"[{url}]({url})"

        pattern = re.compile(r"https?://[^\s)\]]+")
        return pattern.sub(replacer, text)

    def _auto_link_phone_numbers(self, text: str) -> str:
        """Ensure phone numbers are clickable."""
        if not text:
            return text
        import re

        # Match common variations of the phone numbers
        numbers = ["9879972778", "9925822542"]
        # Pattern matches numbers with optional +, optional 91, and optional spaces/dashes
        pattern = re.compile(r"(\+?91[\s-]?)?(" + "|".join(re.escape(n) for n in numbers) + r")")

        def replacer(match: re.Match) -> str:
            full_match = match.group(0)
            clean_number = "+91" + match.group(2)
            start = match.start()
            # Skip if already part of a tel: link or markdown link.
            if start >= 4 and text[start - 4:start] == "tel:":
                return full_match
            if start >= 2 and text[start - 2:start] == "](":
                return full_match
            if start >= 1 and text[start - 1:start] == "[":
                return full_match
            return f"[{full_match}](tel:{clean_number})"

        return pattern.sub(replacer, text)
