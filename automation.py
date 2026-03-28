import os
import json
import requests
import streamlit as st
from tavily import TavilyClient
from provider_manager import ProviderManager

class FinolAutomation:
    def __init__(self, model):
        self.model = model
        
        # Safe loading from st.secrets to prevent blank screen crashes
        self.keys = {
            "GOOGLE_API_KEY": st.secrets.get("GOOGLE_API_KEY", ""),
            "TAVILY_API_KEY": st.secrets.get("TAVILY_API_KEY", ""),
            "TEMPLATED_API_KEY": st.secrets.get("TEMPLATED_API_KEY", ""),
            "OPENROUTER_API_KEY": st.secrets.get("OPENROUTER_API_KEY", ""),
            "OPENROUTER_API_BASE": st.secrets.get("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
            "OR_SITE_URL": st.secrets.get("OR_SITE_URL", ""),
            "OR_APP_NAME": st.secrets.get("OR_APP_NAME", ""),
            "BYTEZ_API_KEY": st.secrets.get("BYTEZ_API_KEY", ""),
        }
        
        # Initialize provider manager for multi-provider fallback
        self.provider_manager = ProviderManager(self.keys)
        
        # Initialization logic
        if not self.keys["TAVILY_API_KEY"]:
            st.error("Missing TAVILY_API_KEY in Streamlit Secrets!")
            self.tavily = None
        else:
            self.tavily = TavilyClient(api_key=self.keys["TAVILY_API_KEY"])

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

    def generate_cover_image(self, topic):
        url = "https://api.templated.io/v1/render"
        headers = {"Authorization": f"Bearer {self.keys['TEMPLATED_API_KEY']}"}
        payload = {
            "template": "d5222a01-a53b-4683-90af-20cd248ebd5f",
            "format": "jpg",
            "layers": {"text-4": {"text": topic}}
        }
        res = requests.post(url, json=payload, headers=headers).json()
        img_res = requests.get(res.get("render_url"))
        return img_res.content

    def upload_to_wordpress(self, title, content, image_bytes, wp_config):
        """Upload blog post with cover image to WordPress."""
        # Clean and validate credentials
        user = str(wp_config.get('user', '')).strip()
        password = str(wp_config.get('pass', '')).strip()
        url = str(wp_config.get('url', '')).strip().rstrip('/')
        
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
                    timeout=30
                )
                
                # Check if response is successful
                if media_response.status_code not in [200, 201]:
                    st.warning(f"Media upload returned {media_response.status_code}. Continuing without featured image.")
                    media_id = None
                else:
                    # Try to parse JSON
                    try:
                        media_res = media_response.json()
                        media_id = media_res.get("id")
                        if media_id:
                            st.success(f"✅ Featured image uploaded successfully!")
                    except:
                        # If JSON parsing fails, try to continue without featured image
                        media_id = None
                    
            except Exception as e:
                # If media upload fails, continue without featured image
                st.warning(f"Cover image upload failed: {str(e)}. Continuing without image.")
                media_id = None
        else:
            st.info("No cover image provided. Publishing without featured image.")
        
        # Create post
        post_url = f"{base_url}/wp-json/wp/v2/posts"
        payload = {
            "title": title,
            "content": content,
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
                timeout=30
            )
            
            # Check if response is successful
            if post_response.status_code == 404:
                # Try alternative URL format (some WordPress setups)
                alt_post_url = f"{base_url}/index.php/wp-json/wp/v2/posts"
                st.info(f"Trying alternative URL: {alt_post_url}")
                
                post_response = requests.post(
                    alt_post_url,
                    json=payload,
                    auth=auth,
                    timeout=30
                )
            
            if post_response.status_code not in [200, 201]:
                error_detail = post_response.text[:500]
                raise Exception(f"Post creation failed: {post_response.status_code} - {error_detail}")
            
            # Try to parse JSON
            try:
                post_res = post_response.json()
                return post_res.get("link", f"{base_url}/?p={post_res.get('id', 'unknown')}")
            except:
                # If JSON parsing fails but post was created, return base URL
                if post_response.status_code in [200, 201]:
                    return f"{base_url}/wp-admin/edit.php"
                raise Exception("Failed to parse WordPress response")
                
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

    def run_writing_pipeline(self, topic, audience, goal, word_target):
        if not self.tavily:
            return "Error: Research tool not initialized."
        
        # Research phase
        res_sys = "Search and prep exactly 5 real article URLs... Return JSON url-1 through url-5."
        search_res = self.tavily.search(query=f"{topic} {audience}")
        urls = [r['url'] for r in search_res['results'][:5]]
        
        # SEO phase - Focus on natural keyword integration
        seo_sys = """You are a modern SEO specialist (2026 standards). 
        Identify 3-5 PRIMARY keywords that are closely related and natural.
        Avoid keyword stuffing - focus on semantic relevance and user intent.
        Return JSON with:
        - 'primary_keyword': The main focus keyword (1-3 words)
        - 'related_keywords': 2-4 closely related semantic variations
        - 'lsi_keywords': 3-5 Latent Semantic Indexing terms (natural synonyms)
        
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
                "related_keywords": [audience],
                "lsi_keywords": ["solutions", "strategies", "benefits"]
            }

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
        writer_sys = """You are an expert content writer creating engaging, natural blog content.

CRITICAL RULES FOR MODERN SEO (2026):
1. Write for HUMANS first, search engines second
2. Use keywords NATURALLY - never force them
3. Vary your language - use synonyms and semantic variations
4. Focus on providing VALUE and answering user intent
5. Avoid repetitive phrases and keyword stuffing
6. Write conversationally and authentically

KEYWORD USAGE GUIDELINES:
- Primary keyword: Use 2-3 times naturally in the entire section
- Related keywords: Sprinkle 1-2 times if they fit naturally
- LSI keywords: Use freely as they're natural synonyms
- NEVER start multiple paragraphs with the same keyword phrase
- NEVER repeat exact keyword phrases back-to-back

WRITING STYLE:
- Conversational and engaging
- Clear and concise
- Use examples and stories
- Break up text with varied sentence structure
- Focus on reader benefit

INCLUDE NATURALLY (not forced):
- Contact: +919879972778 or +919925822542 (mention once, contextually)

Return JSON with 'section_markdown' field containing well-written content.

BAD EXAMPLE (keyword stuffing):
"From AI content generation for agencies to sophisticated AI creator systems advertising, AI workflow ad agencies are transforming. AI strategy ad agencies using AI tools for ad agencies..."

GOOD EXAMPLE (natural):
"Modern agencies are discovering how artificial intelligence transforms their workflow. From content creation to campaign optimization, these tools are reshaping how teams work..."
"""
        
        for section in outline['sections']:
            section_title = section.get('title', 'Section') if isinstance(section, dict) else str(section)
            section_words = section.get('word_count', 200) if isinstance(section, dict) else 200
            section_focus = section.get('focus', 'Provide value') if isinstance(section, dict) else 'Provide value'
            
            section_input = f"""
Section Title: {section_title}
Target Words: {section_words}
Section Focus: {section_focus}

SEO Keywords (use naturally, don't force):
- Primary: {seo_data.get('primary_keyword', topic)}
- Related: {', '.join(seo_data.get('related_keywords', [])[:3])}
- LSI: {', '.join(seo_data.get('lsi_keywords', [])[:5])}

Context: {topic} for {audience}
Goal: {goal}

Previous content (for context, don't repeat): {blog_content[-300:] if blog_content else 'This is the first section'}

Write engaging, natural content that provides real value. Avoid keyword stuffing.
"""
            
            try:
                written = self.ai_call(writer_sys, section_input)
                
                # Handle different response formats
                if isinstance(written, dict):
                    if 'section_markdown' in written:
                        blog_content += f"\n\n{written['section_markdown']}"
                    elif 'content' in written:
                        blog_content += f"\n\n{written['content']}"
                    elif 'raw_content' in written:
                        blog_content += f"\n\n{written['raw_content']}"
                    else:
                        # If no expected field, use the whole dict as string
                        blog_content += f"\n\n## {section_title}\n\n{str(written)}"
                elif isinstance(written, str):
                    blog_content += f"\n\n## {section_title}\n\n{written}"
                else:
                    blog_content += f"\n\n## {section_title}\n\n{str(written)}"
                    
            except Exception as e:
                # If section writing fails, add a placeholder
                blog_content += f"\n\n## {section_title}\n\n[Content generation failed for this section: {str(e)}]"
            
        return blog_content