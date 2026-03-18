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
        auth = (wp_config['user'], wp_config['pass'])
        base_url = wp_config['url'].rstrip('/')
        
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
                raise Exception(f"Media upload failed: {media_response.status_code} - {media_response.text[:200]}")
            
            # Try to parse JSON
            try:
                media_res = media_response.json()
                media_id = media_res.get("id")
            except:
                # If JSON parsing fails, try to continue without featured image
                media_id = None
                
        except Exception as e:
            # If media upload fails, continue without featured image
            st.warning(f"Cover image upload failed: {str(e)}. Continuing without image.")
            media_id = None
        
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
            post_response = requests.post(
                post_url, 
                json=payload, 
                auth=auth,
                timeout=30
            )
            
            # Check if response is successful
            if post_response.status_code not in [200, 201]:
                raise Exception(f"Post creation failed: {post_response.status_code} - {post_response.text[:200]}")
            
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
            raise Exception(f"WordPress publishing failed: {str(e)}")

    def run_writing_pipeline(self, topic, audience, goal, word_target):
        if not self.tavily:
            return "Error: Research tool not initialized."
        
        # Research phase
        res_sys = "Search and prep exactly 5 real article URLs... Return JSON url-1 through url-5."
        search_res = self.tavily.search(query=f"{topic} {audience}")
        urls = [r['url'] for r in search_res['results'][:5]]
        
        # SEO phase
        seo_sys = "You are a blog SEO specialist. Identify primary and supporting keywords. Return JSON with 'primary_keywords' and 'supporting_keywords' fields."
        seo_data = self.ai_call(seo_sys, f"Topic: {topic}, Sources: {urls}")
        
        # Handle SEO data parsing errors
        if isinstance(seo_data, dict) and "error" in seo_data:
            seo_data = {"primary_keywords": [topic], "supporting_keywords": [audience, goal]}

        # Outline phase
        map_sys = "You are a blog outline planning agent. Create an outline with sections. Return JSON with 'sections' array containing section objects with 'title' and 'word_count' fields."
        outline = self.ai_call(map_sys, f"Topic: {topic}, Target: {word_target}, Goal: {goal}")
        
        # Handle outline parsing errors
        if isinstance(outline, dict) and "error" in outline:
            # Create a default outline
            outline = {
                "sections": [
                    {"title": "Introduction", "word_count": word_target // 4},
                    {"title": "Main Content", "word_count": word_target // 2},
                    {"title": "Conclusion", "word_count": word_target // 4}
                ]
            }
        
        # Ensure sections exist
        if not isinstance(outline, dict) or 'sections' not in outline:
            outline = {
                "sections": [
                    {"title": "Introduction", "word_count": word_target // 4},
                    {"title": "Main Content", "word_count": word_target // 2},
                    {"title": "Conclusion", "word_count": word_target // 4}
                ]
            }

        # Writing phase
        blog_content = ""
        writer_sys = "You are a blog section writer. Write engaging content. CTA: Include +919879972778 or +919925822542. Return JSON with 'section_markdown' field containing the written content."
        
        for section in outline['sections']:
            section_title = section.get('title', 'Section') if isinstance(section, dict) else str(section)
            section_words = section.get('word_count', 200) if isinstance(section, dict) else 200
            
            section_input = f"Section: {section_title}, Target words: {section_words}, Keywords: {seo_data}, Blog so far: {blog_content[:500]}"
            
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