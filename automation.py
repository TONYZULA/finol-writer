import os
import json
import requests
import streamlit as st
from litellm import completion
from litellm.exceptions import (
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)
from tavily import TavilyClient

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
        }
        
        # Initialization logic
        if not self.keys["TAVILY_API_KEY"]:
            st.error("Missing TAVILY_API_KEY in Streamlit Secrets!")
            self.tavily = None
        else:
            self.tavily = TavilyClient(api_key=self.keys["TAVILY_API_KEY"])
        
        # Set environment variables for LiteLLM
        os.environ["GOOGLE_API_KEY"] = self.keys["GOOGLE_API_KEY"]
        os.environ["OPENROUTER_API_KEY"] = self.keys["OPENROUTER_API_KEY"]
        os.environ["OPENROUTER_API_BASE"] = self.keys["OPENROUTER_API_BASE"]
        if self.keys["OR_SITE_URL"]:
            os.environ["OR_SITE_URL"] = self.keys["OR_SITE_URL"]
        if self.keys["OR_APP_NAME"]:
            os.environ["OR_APP_NAME"] = self.keys["OR_APP_NAME"]

        self._normalized_model = self._normalize_model_name(self.model)
        self._validate_provider_keys()

    def _normalize_model_name(self, model: str) -> str:
        """
        Streamlit UI uses friendly model IDs. LiteLLM expects provider prefixes.
        - Direct Gemini (API key) uses: gemini/gemini-*
        - OpenRouter uses: openrouter/<provider>/<model>
        """
        m = (model or "").strip()
        if m.startswith("google/gemini-"):
            # Map "google/gemini-2.5-pro" -> "gemini/gemini-2.5-pro"
            return "gemini/" + m.replace("google/", "", 1)
        return m

    def _validate_provider_keys(self) -> None:
        m = self._normalized_model
        if m.startswith("openrouter/") and not self.keys["OPENROUTER_API_KEY"]:
            st.error("Missing OPENROUTER_API_KEY in Streamlit Secrets (required for OpenRouter models).")
        if m.startswith("gemini/") and not self.keys["GOOGLE_API_KEY"]:
            st.error("Missing GOOGLE_API_KEY in Streamlit Secrets (required for direct Gemini models).")

    def ai_call(self, system_prompt, user_prompt, json_mode=True):
        model = self._normalized_model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Explicit base_url improves reliability on some LiteLLM versions/environments
        base_url = self.keys["OPENROUTER_API_BASE"] if model.startswith("openrouter/") else None

        last_err = None
        for attempt in range(1, 4):
            try:
                response = completion(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"} if json_mode else None,
                    base_url=base_url,
                    timeout=60,
                )
                content = response.choices[0].message.content or ""
                return self._safe_json_loads(content) if json_mode else content
            except (APIConnectionError, RateLimitError) as e:
                last_err = e
                # Basic backoff (1s, 2s, 4s)
                import time
                time.sleep(2 ** (attempt - 1))
                continue
            except AuthenticationError as e:
                raise RuntimeError(
                    "Authentication failed. Verify the correct API key is set in Streamlit Secrets "
                    f"for model={model}."
                ) from e
            except BadRequestError as e:
                # Some models don't support response_format; retry once without JSON mode.
                if json_mode:
                    json_mode = False
                    continue
                raise
        raise last_err if last_err else RuntimeError("LLM call failed for unknown reasons.")

    def _safe_json_loads(self, text: str):
        try:
            return json.loads(text)
        except Exception:
            # Attempt to recover JSON object embedded in extra text
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
            raise

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
        auth = (wp_config['user'], wp_config['pass'])
        base_url = wp_config['url'].rstrip('/')
        media_url = f"{base_url}/wp-json/wp/v2/media"
        headers = {"Content-Disposition": 'attachment; filename="cover.jpg"', "Content-Type": "image/jpeg"}
        media_res = requests.post(media_url, data=image_bytes, headers=headers, auth=auth).json()
        
        post_url = f"{base_url}/wp-json/wp/v2/posts"
        payload = {"title": title, "content": content, "status": "publish", "featured_media": media_res.get("id")}
        post_res = requests.post(post_url, json=payload, auth=auth).json()
        return post_res.get("link")

    def run_writing_pipeline(self, topic, audience, goal, word_target):
        if not self.tavily:
            return "Error: Research tool not initialized."
        
        res_sys = "Search and prep exactly 5 real article URLs... Return JSON url-1 through url-5."
        search_res = self.tavily.search(query=f"{topic} {audience}")
        urls = [r['url'] for r in search_res['results'][:5]]
        
        seo_sys = "You are a blog SEO specialist. Identify primary and supporting keywords. Return JSON."
        seo_data = self.ai_call(seo_sys, f"Topic: {topic}, Sources: {urls}")

        map_sys = "You are a blog outline planning agent. Sum of word counts must match target."
        outline = self.ai_call(map_sys, f"Topic: {topic}, Target: {word_target}")

        blog_content = ""
        writer_sys = "You are a blog section writer. CTA: Include +919879972778 or +919925822542. Output JSON."
        for section in outline['sections']:
            section_input = f"Section: {section}, Keywords: {seo_data}, Blog so far: {blog_content}"
            written = self.ai_call(writer_sys, section_input)
            blog_content += f"\n\n{written['section_markdown']}"
            
        return blog_content