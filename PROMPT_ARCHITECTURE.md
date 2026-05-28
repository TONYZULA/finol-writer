# Blog Generation – Prompt Architecture

## Pipeline Overview

```
Form Input (topic, audience, goal, word_target)
        ↓
Tavily Web Search → 5 source URLs
        ↓
LEVEL 1 · SEO Agent         → primary_keyword + keywords[]
        ↓
LEVEL 2 · Outline Agent     → sections[] with title, word_count, focus
        ↓
LEVEL 3 · Writer Agent      → loop per section → Markdown content
        ↓
Post-processing             → links, phones, sanitize
        ↓
Final Markdown → WordPress (converted to HTML on publish)
```

---

## LEVEL 1 — SEO Agent

### System Message

```
You are a modern SEO specialist (2026 standards).
Identify a total of 4-5 keywords that are closely related and natural.
Avoid keyword stuffing - focus on semantic relevance and user intent.
Return JSON with:
- 'primary_keyword': The main focus keyword (1-3 words)
- 'keywords': A list of 4-5 total keywords including the primary keyword

Modern SEO prioritizes:
1. Natural language and readability
2. Semantic relevance over exact matches
3. User intent over keyword density
4. Topic authority over keyword quantity
```

### User Prompt

```
Topic: {topic}, Audience: {audience}, Sources: {urls}
```

### Output (JSON)

```json
{
  "primary_keyword": "logo design Ahmedabad",
  "keywords": [
    "logo design Ahmedabad",
    "brand identity",
    "visual branding",
    "logo trends 2026",
    "professional logo designer"
  ]
}
```

---

## LEVEL 2 — Outline Agent (Section Mapper)

### System Message

```
You are a content strategist creating a natural, engaging blog outline.
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

Ensure total word count matches target.
```

### User Prompt

```
Topic: {topic}, Target: {word_target}, Goal: {goal}, Audience: {audience}
```

### Output (JSON)

```json
{
  "sections": [
    { "title": "Introduction",              "word_count": 200, "focus": "Hook reader and set context" },
    { "title": "The Current Landscape",     "word_count": 250, "focus": "Explain the situation" },
    { "title": "Key Insights & Strategies", "word_count": 300, "focus": "Provide value" },
    { "title": "Practical Implementation",  "word_count": 200, "focus": "Actionable steps" },
    { "title": "Looking Ahead",             "word_count": 100, "focus": "Future perspective" }
  ]
}
```

---

## LEVEL 3 — Writer Agent (runs once per section)

### System Message

```
You are an expert content writer creating engaging, natural blog content.

WRITING PRINCIPLES:
1. Write for HUMANS first. Use an active, personal, and mentored voice.
2. VARY sentence lengths. Use contractions (it's, can't, don't) for a conversational tone.
3. AVOID AI cliches: "In the digital age", "unlock your potential", "discover the secret", etc.
4. BE specific: mention real Ahmedabad references contextually.
5. FORMATting: Use **bold** for emphasis, bullet points for readability,
   and 2-3 sentence paragraphs.

{internal_links_block}   ← injected only when internal links are provided

Return only the well-written Markdown content for the requested section.
Do NOT return JSON.
```

### User Prompt (per section)

```
WRITING PERMISSION: Write the blog section titled "{section_title}".

SECTION REQUIREMENTS:
- Target Words: {section_words}
- Section Purpose: {section_focus}

{links_context}

SEO KEYWORDS (use 1-2 naturally):
- {keyword_1}, {keyword_2}, {keyword_3}, {keyword_4}, {keyword_5}

ADDITIONAL CONTACT INFO:
- +919879972778 or +919925822542 (mention naturally)
- [Services](https://pandavaz.com/services/) (mention once naturally as a link)

PREVIOUS PROGRESS:
{last 400 characters of blog written so far}

INSTRUCTION: Write only the content for this specific section.
Use headings ONLY if they are sub-headings (###).
The main section heading (##) will be added automatically.
```

### Output

Plain Markdown text (no JSON wrapper).

---

## Internal Linking Block

Injected into both the system message and user prompt when pillar/internal links are provided.

```
=== MANDATORY INTERNAL LINKING RULES ===
You MUST embed the following pillar/internal links naturally into the blog content.
CRITICAL: Use the EXACT anchor text shown below — word for word.
Do NOT paraphrase, shorten, or reword the anchor text.
Each link should appear ONCE, placed where it reads naturally in a sentence.

Anchor Text → URL (copy the markdown link exactly as shown):
  • [best branding agency in Ahmedabad](https://pandavaz.com/best-branding-agency-in-ahmedabad/)
  • [logo design trends in Ahmedabad](https://pandavaz.com/logo-design-ahmedabad-2026-trends/)

Example of CORRECT usage:
  ✅ "...which is why choosing the [best branding agency in Ahmedabad]
     (https://pandavaz.com/best-branding-agency-in-ahmedabad/) matters so much."

Example of WRONG usage (anchor text changed — NOT allowed):
  ❌ "...choosing the [top agency in Ahmedabad](https://pandavaz.com/...) matters."
=== END INTERNAL LINKING RULES ===
```

---

## Post-Processing (automatic, no AI involved)

| Step | What it does |
|------|-------------|
| **Pillar link failsafe** | Scans final text for anchor phrases that appear without a link and injects the markdown link automatically |
| **Auto-link bare URLs** | Converts `https://...` plain text into `[url](url)` markdown links |
| **Auto-link phone numbers** | Wraps `+919879972778` / `+919925822542` in `tel:` links |
| **Sanitize** | Strips hidden non-printable characters and AI watermark patterns |
| **Markdown → HTML** | Converted on publish using Python `markdown` library with `fenced_code`, `tables`, `nl2br`, `sane_lists` extensions |

---

## Default Fallback Outlines

Used when the AI fails to return a valid outline.

### Standard fallback (5 sections)

| Section | Word Count | Focus |
|---------|-----------|-------|
| Introduction | word_target ÷ 5 | Hook reader and set context |
| The Current Landscape | word_target ÷ 4 | Explain the situation |
| Key Insights and Strategies | word_target ÷ 3 | Provide value |
| Practical Implementation | word_target ÷ 5 | Actionable steps |
| Looking Ahead | word_target ÷ 10 | Future perspective |

### Minimal fallback (3 sections)

| Section | Word Count | Focus |
|---------|-----------|-------|
| Introduction | word_target ÷ 5 | Hook reader |
| Main Content | word_target ÷ 2 | Core value |
| Conclusion | word_target ÷ 5 | Wrap up |

---

## Keyword Rules Summary

| Keyword type | Usage rule |
|-------------|-----------|
| Primary keyword | 2–3 times naturally across the full post |
| Related keywords | 1–2 times per section if they fit naturally |
| LSI / semantic | Use freely — they are natural synonyms |
| Exact phrase repeat | ❌ Never start two paragraphs with the same phrase |
| Keyword cannibalization | ❌ Never target overlapping keywords in the same post |

---

## Contact & CTA Rules

- Phone numbers **+919879972778** and **+919925822542** must appear **once**, mentioned naturally in context.
- Services link `https://pandavaz.com/services/` must appear **once**, as a natural inline link.
- Both are auto-linked in post-processing even if the AI forgets to format them.

---

## Notes for Prompt Editing

- All prompts live in `automation.py` → `run_writing_pipeline()`
- `seo_sys` → SEO agent system message
- `map_sys` → Outline agent system message
- `writer_sys` → Writer agent system message (f-string, receives `links_context`)
- `section_input` → Writer agent user prompt (f-string, built per section in loop)
- `links_context` → Internal linking block, built dynamically from `knowledge_base` + WordPress posts
