import os
import json
import requests
import streamlit as st
from litellm import completion
from tavily import TavilyClient

class FinolAutomation:
    def __init__(self, model, api_keys=None):
        """
        Initializes the automation engine using Streamlit Secrets for credentials.
        """
        self.model = model
        
        # Load API keys directly from st.secrets
        # This replaces the need for local .env files or hard-coding
        self.keys = {
            "GOOGLE_API_KEY": st.secrets["GOOGLE_API_KEY"],
            "TAVILY_API_KEY": st.secrets["TAVILY_API_KEY"],
            "TEMPLATED_API_KEY": st.secrets["TEMPLATED_API_KEY"],
            "OPENROUTER_API_KEY": st.secrets.get("OPENROUTER_API_KEY", "")
        }
        
        # Initialize Tavily client
        self.tavily = TavilyClient(api_key=self.keys["TAVILY_API_KEY"])
        
        # Set environment variables for LiteLLM and other drivers
        os.environ["GOOGLE_API_KEY"] = self.keys["GOOGLE_API_KEY"]
        os.environ["OPENROUTER_API_KEY"] = self.keys["OPENROUTER_API_KEY"]

    def ai_call(self, system_prompt, user_prompt, json_mode=True):
        """Universal AI caller for swappable models."""
        response = completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"} if json_mode else None
        )
        return json.loads(response.choices[0].message.content)

    def generate_cover_image(self, topic):
        """Triggers Templated.io and downloads binary image data."""
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
        """Uploads media and publishes post to an online WP site."""
        auth = (wp_config['user'], wp_config['pass'])
        base_url = wp_config['url'].rstrip('/')

        # 1. Upload Media
        media_url = f"{base_url}/wp-json/wp/v2/media"
        headers = {
            "Content-Disposition": 'attachment; filename="cover.jpg"', 
            "Content-Type": "image/jpeg"
        }
        media_res = requests.post(media_url, data=image_bytes, headers=headers, auth=auth).json()
        
        # 2. Create Post
        post_url = f"{base_url}/wp-json/wp/v2/posts"
        payload = {
            "title": title, 
            "content": content, 
            "status": "publish",
            "featured_media": media_res.get("id")
        }
        post_res = requests.post(post_url, json=payload, auth=auth).json()
        return post_res.get("link")

    def run_writing_pipeline(self, topic, audience, goal, word_target):
        """Executes the n8n research and writing logic sequence."""
        # Researcher Prompt (Original JSON Prompt)
        res_sys = "Search and prep exactly 5 real article URLs... Return JSON url-1 through url-5."
        search_res = self.tavily.search(query=f"{topic} {audience}")
        urls = [r['url'] for r in search_res['results'][:5]]
        
        # SEO Prompt (Original JSON Prompt)
        seo_sys = "You are a blog SEO specialist. Identify primary and supporting keywords. Return JSON."
        seo_data = self.ai_call(seo_sys, f"Topic: {topic}, Sources: {urls}")

        # Section Mapper Prompt (Original JSON Prompt)
        map_sys = "You are a blog outline planning agent. Sum of word counts must match target."
        outline = self.ai_call(map_sys, f"Topic: {topic}, Target: {word_target}")

        # Iterative Writing Loop
        blog_content = ""
        writer_sys = "You are a blog section writer. CTA: Include +919879972778 or +919925822542. Output JSON."
        for section in outline['sections']:
            section_input = f"Section: {section}, Keywords: {seo_data}, Blog so far: {blog_content}"
            written = self.ai_call(writer_sys, section_input)
            blog_content += f"\n\n{written['section_markdown']}"
            
        return blog_content