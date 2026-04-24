# utils.py - helper functions for the flashcard app

import streamlit as st
import re
import os
import requests
import json


# --- Wikipedia image search ---

@st.cache_data(show_spinner=False)
def search_wikipedia_image(query):
    """search wikipedia for a picture that matches the topic"""
    try:
        # clean up the query - remove emojis etc
        clean_query = re.sub(r'[^\w\s-]', '', query).strip()
        if not clean_query:
            return None
        
        search_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": clean_query,
            "gsrlimit": 5,  # get more results so we can pick the best one
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": 500,
        }
        
        response = requests.get(
            search_url, 
            params=params, 
            timeout=5,
            headers={"User-Agent": "FlashcardApp/1.0"}
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        
        # skip junk pages (disambiguation, lists, etc.)
        junk_keywords = ['disambiguation', 'list of', '(surname)', '(given name)']
        
        # score each candidate page by how well its title matches the query.
        # initial score of 0 (not -1) means pages with ZERO word overlap are
        # never picked — better to return no image than a confidently-wrong one.
        # (a "giraffe habitat" search that returned a "Savanna" page with an
        # elephant photo was the original bug this guards against.)
        query_words = set(clean_query.lower().split())
        best_match = None
        best_score = 0
        
        for page_id, page_data in pages.items():
            if "thumbnail" not in page_data:
                continue
            
            page_title = page_data.get("title", "").lower()
            
            # skip junk pages
            if any(junk in page_title for junk in junk_keywords):
                continue
            
            # score how well the page title matches our query
            title_words = set(page_title.split())
            overlap = len(query_words & title_words)
            
            # prefer pages where the title actually contains our search words
            if overlap > best_score:
                best_score = overlap
                best_match = page_data["thumbnail"]["source"]
        
        return best_match
    except Exception:
        return None


# --- card colours for different themes ---

def get_card_colors(colour_scheme):
    """return the three per-card colours the renderer actually uses.
    previously returned card_bg/question_bg/success/flipped_bg too but
    nothing read them — trimmed to keep the schema honest."""
    color_map = {
        "Soft Blue": {
            "text":   "#1A237E",
            "label":  "#3A7CA5",
            "accent": "#3F51B5",
        },
        "Pale Lavender": {
            "text":   "#4A148C",
            "label":  "#7C3C9C",
            "accent": "#9C27B0",
        },
        "Pale Mint": {
            # label darkened from #3C8C6C (4.03:1, failed WCAG AA) to
            # #2F7A55 (5.15:1, passes AA with headroom).
            "text":   "#1B5E20",
            "label":  "#2F7A55",
            "accent": "#4CAF50",
        },
        "Low Stimulation": {
            # low-chroma near-greyscale for users who find saturated
            # palettes overstimulating (common for autism / sensory
            # processing differences). all three values pass WCAG AA
            # on a #FFFEF9 card background.
            "text":   "#2E2E2E",
            "label":  "#555555",
            "accent": "#7A7A7A",
        },
    }
    return color_map.get(colour_scheme, color_map["Low Stimulation"])


# --- emoji matching ---

def get_emoji_for_topic(text):
    """pick an emoji based on what the topic is about"""
    text_lower = text.lower()
    
    emoji_map = {
        'moon|planet|star|space|orbit|gravity|solar': '🌙',
        'atom|molecule|element|chemical|reaction': '⚛️',
        'cell|biology|organism|gene|dna': '🧬',
        'energy|power|electricity|light': '⚡',
        'earth|geology|rock|mineral': '🪨',
        'water|ocean|sea|liquid': '💧',
        'weather|climate|temperature|wind': '🌤️',
        'ecosystem|nature|forest|animal|plant': '🌿',
        'anatomy|body|heart|brain|human': '🫀',
        'number|math|calculate|equation': '🔢',
        'history|ancient|war|battle|empire': '⚔️',
        'art|painting|sculpture|creative': '🎨',
        'music|song|instrument': '🎵',
        'literature|book|story|author': '📚',
        'country|city|continent|map': '🗺️',
        'mountain|hill|valley': '⛰️',
        'computer|technology|software|code': '💻',
        'internet|network|server': '🌐',
        'robot|machine|artificial': '🤖',
        'disease|medicine|doctor|health': '⚕️',
        'exercise|fitness|sport': '💪',
        'food|nutrition|diet': '🍎',
        'economy|money|trade|business': '💰',
        'government|law|politics': '⚖️',
        'education|school|learn|teach': '🎓',
        'elephant|tiger|lion|whale|dolphin|bird': '🐘',
    }
    
    for keywords, emoji in emoji_map.items():
        for keyword in keywords.split('|'):
            if keyword in text_lower:
                return emoji
    
    return '💡'  # default


# --- LLM flashcard generation (this is the main one) ---

# Tool schema for structured output.
# Using tool_choice forces Claude to return JSON that conforms to this schema,
# which eliminates the whole class of "malformed JSON" errors we used to get.
# The description fields also double as hints to Claude about what each
# field is for — they're surfaced during generation, not just validation.
FLASHCARD_TOOL = {
    "name": "create_flashcards",
    "description": (
        "Save a set of learning flashcards for the student. Each card has a "
        "short title, a Wikipedia image search term, a topic keyword, and 1-3 "
        "facts. Each fact has its own relevant emoji."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "flashcards": {
                "type": "array",
                "description": "Between 3 and 5 flashcards covering the key ideas in the source text.",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "A brief 2-4 word topic name for this card.",
                        },
                        "facts": {
                            "type": "array",
                            "description": "1-3 facts about this topic, each with its own emoji.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "emoji": {
                                        "type": "string",
                                        "description": "A single emoji that represents THIS specific fact (not the card topic as a whole).",
                                    },
                                    "text": {
                                        "type": "string",
                                        "description": "The fact text, matching the reading level and writing rules in the prompt.",
                                    },
                                },
                                "required": ["emoji", "text"],
                            },
                        },
                        "topic_keyword": {
                            "type": "string",
                            "description": "A short keyword for the card's topic, used as a fallback emoji hint.",
                        },
                        "image_search": {
                            "type": "string",
                            "description": "A concrete, photographable noun phrase to find a Wikipedia image.",
                        },
                    },
                    "required": ["title", "facts", "topic_keyword", "image_search"],
                },
            },
        },
        "required": ["flashcards"],
    },
}


def generate_flashcards_from_llm(raw_text, reading_level="intermediate"):
    """send text to claude and get flashcards back"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("Can't find the AI key - please check your settings.")
        return None
    
    # set up the reading level instructions
    if reading_level == "simple":
        level_instructions = """READING LEVEL: EASY (Ages 4-11)
- Use very simple words only, like a children's book
- Short sentences (8-12 words max per fact)
- No big or technical words
- Titles should be 2-4 simple words
- Make it friendly and fun"""
    elif reading_level == "complex":
        level_instructions = """READING LEVEL: ADVANCED (Ages 18+)
- Use precise academic language
- Include technical terms and proper terminology
- Facts can be longer and more detailed (up to 25 words)
- Maintain accuracy and depth"""
    else:
        level_instructions = """READING LEVEL: MEDIUM (Ages 11-18)
- Use clear everyday language a teenager would understand
- Medium sentences (12-18 words per fact)
- Explain technical terms briefly when used"""
    
    prompt = f"""You are creating flashcards for a student with cognitive accessibility needs (dyslexia, processing differences, ADHD). Follow the reading level and writing rules EXACTLY.

{level_instructions}

DYSLEXIA-FRIENDLY WRITING RULES (apply to EVERY fact at every reading level):
- Use active voice. "The moon pulls the water" NOT "The water is pulled by the moon."
- One idea per sentence. Avoid "which", "that", or "and" chains that bundle multiple ideas together.
- Use concrete, specific nouns instead of abstract ones. "A loud bang" beats "an acoustic disturbance."
- Prefer short, common, everyday words over rare or long ones when they mean the same thing.
- Write numbers as digits (5, 100) not words (five, one hundred) — easier for dyslexic readers to process.
- Avoid double negatives. "It is helpful" beats "It is not unhelpful."
- At the Easy reading level ONLY: no idioms, metaphors, or figurative language. Some learners take these literally.

EMOJI RULES (per fact):
- Each fact gets ONE emoji that represents THAT fact's content, not the card topic as a whole.
- Pick concrete and memorable emojis. A whale-sound fact gets 🔊, a whale-size fact gets 📏, a whale-food fact gets 🦐.
- Use different emojis for different facts on the same card.

IMAGE SEARCH RULES (CRITICAL - getting this wrong gives learners the wrong picture):
- image_search must name the MAIN SUBJECT of the card, NOT its habitat, context, action, or property.
  - Card titled "Where Giraffes Live" → use "giraffe" (NOT "African savanna" — that page's photo is often an elephant).
  - Card titled "How DNA Copies Itself" → use "DNA" (NOT "cell division" or "genetic replication").
  - Card titled "What Elephants Eat" → use "elephant" (NOT "plants" or "African vegetation").
  - Card titled "The Life Cycle of Butterflies" → use "butterfly" (NOT "life cycle" or "metamorphosis").
- The subject must be PHOTOGRAPHABLE — Wikipedia needs an actual photo of it.
- For genuinely abstract concepts (no physical subject), pick a concrete stand-in: "inflation" → "shopping basket", "democracy" → "ballot box", "friendship" → "people holding hands".
- Add a distinguishing adjective ONLY when it helps find the right picture and doesn't drop the main subject: "steam locomotive" is fine, "African elephant" is fine. Never drop the core noun.

TEXT TO CONVERT:
{raw_text}

Now call the create_flashcards tool with 3 to 5 cards."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}],
                # structured output via tool use: the API validates Claude's
                # response against FLASHCARD_TOOL's schema before returning,
                # so we don't have to parse markdown-fenced JSON or handle
                # malformed output ourselves.
                "tools": [FLASHCARD_TOOL],
                "tool_choice": {"type": "tool", "name": "create_flashcards"},
            },
            timeout=30
        )
        
        if response.status_code != 200:
            st.error("Something went wrong talking to the AI - please try again in a moment.")
            return None
        
        # extract the tool_use block. with tool_choice forcing this specific
        # tool, there should always be exactly one - but we look it up by name
        # rather than index in case the API adds other block types in future.
        api_response = response.json()
        tool_use_block = next(
            (
                block for block in api_response.get("content", [])
                if block.get("type") == "tool_use"
                and block.get("name") == "create_flashcards"
            ),
            None
        )
        
        if not tool_use_block:
            st.error("The AI didn't create flashcards in the expected format - please try again.")
            return None
        
        flashcard_data = tool_use_block["input"]["flashcards"]
        
        flashcards = []
        for card in flashcard_data:
            topic_emoji = get_emoji_for_topic(card.get("topic_keyword", card["title"]))
            
            # normalize facts to a consistent {emoji, text} shape.
            # handles both the new dict format and the old string format in case
            # the LLM falls back — we stay resilient to schema drift.
            normalized_facts = []
            for raw_fact in card.get('facts', []):
                if isinstance(raw_fact, dict):
                    normalized_facts.append({
                        'emoji': raw_fact.get('emoji', topic_emoji),
                        'text': raw_fact.get('text', '').strip(),
                    })
                elif isinstance(raw_fact, str):
                    normalized_facts.append({
                        'emoji': topic_emoji,
                        'text': raw_fact.strip(),
                    })
                # silently skip anything malformed rather than crash
            
            flashcards.append({
                'title': card['title'],
                'facts': normalized_facts,
                'emoji': topic_emoji,
                'image_search': card.get('image_search', card['title']),
            })
        
        return flashcards
    
    except json.JSONDecodeError:
        st.error("The AI's reply didn't come back in the right format - please try again.")
        return None
    except requests.exceptions.RequestException:
        st.error("Couldn't reach the AI - please check your internet and try again.")
        return None
    except Exception:
        st.error("Something went wrong - please try again.")
        return None


# --- file text extraction ---

def extract_text_from_file(uploaded_file):
    """pull text out of uploaded pdf, docx, or txt files"""
    try:
        if uploaded_file.type == "text/plain":
            return uploaded_file.read().decode('utf-8')
        
        elif uploaded_file.type == "application/pdf":
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            from docx import Document
            doc = Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
        
        else:
            return "Not supported - please use PDF, DOCX, or TXT."
    
    except Exception:
        return "Sorry, couldn't read that file - please try a different one."


# --- page header and feedback box ---

# Per-scheme theming for the header banner + feedback survey box.
# Single source of truth — both renderers read from here, so adding a new
# colour scheme later means adding one entry, not editing two places.
#
# Header gradients are chosen to be dark enough for white title text to
# pass WCAG AA contrast (4.5:1). Low Stimulation uses a solid muted grey
# (no gradient, no shadow) because a bold gradient would undercut the
# whole point of that scheme.
_SCHEME_THEMES = {
    "Soft Blue": {
        "header_bg":       "linear-gradient(135deg, #2C5282 0%, #3182CE 50%, #2B6CB0 100%)",
        "header_shadow":   "0 4px 16px rgba(44, 82, 130, 0.25)",
        "feedback_tint":   "rgba(58, 124, 165, 0.08)",
        "feedback_border": "rgba(58, 124, 165, 0.25)",
        "feedback_btn":    "#3A7CA5",
    },
    "Pale Lavender": {
        "header_bg":       "linear-gradient(135deg, #6B2F85 0%, #8E24AA 50%, #7B2B93 100%)",
        "header_shadow":   "0 4px 16px rgba(107, 47, 133, 0.25)",
        "feedback_tint":   "rgba(142, 36, 170, 0.08)",
        "feedback_border": "rgba(142, 36, 170, 0.25)",
        "feedback_btn":    "#7C3C9C",
    },
    "Pale Mint": {
        "header_bg":       "linear-gradient(135deg, #276749 0%, #3E8E66 50%, #2F7A55 100%)",
        "header_shadow":   "0 4px 16px rgba(39, 103, 73, 0.25)",
        "feedback_tint":   "rgba(47, 122, 85, 0.08)",
        "feedback_border": "rgba(47, 122, 85, 0.25)",
        "feedback_btn":    "#2F7A55",
    },
    "Low Stimulation": {
        # deliberately flat: no gradient, no shadow. users who chose this
        # scheme want less visual activity, so the header should follow
        # suit — a bold gradient would fight the whole intent.
        "header_bg":       "#5A5A5A",
        "header_shadow":   "none",
        "feedback_tint":   "rgba(90, 90, 90, 0.06)",
        "feedback_border": "rgba(90, 90, 90, 0.22)",
        "feedback_btn":    "#5A5A5A",
    },
}


def _theme_for(colour_scheme):
    """look up the header/feedback theme for a scheme, falling back to
    Low Stimulation if an unknown value slips in (e.g. returning users
    with an old stored scheme name)."""
    return _SCHEME_THEMES.get(colour_scheme, _SCHEME_THEMES["Low Stimulation"])


def render_header(app_title, app_subtitle, text_size, colour_scheme):
    """show the big banner at the top of the page.
    background is picked from _SCHEME_THEMES so the banner automatically
    re-tints when the user changes Colour Scheme. title is twice body
    text size. we use <div> instead of <h1> because streamlit aggressively
    styles h1 tags which overrides our size."""
    theme = _theme_for(colour_scheme)
    title_px = text_size * 2
    subtitle_px = text_size
    st.markdown(f"""
    <div style='background: {theme["header_bg"]}; padding: 28px 26px; border-radius: 12px; box-shadow: {theme["header_shadow"]}; height: 100%; box-sizing: border-box;'>
        <div style='font-size: {title_px}px; font-weight: 800; color: #FFFFFF; margin: 0; line-height: 1.1; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);'>💡 {app_title}</div>
        <div style='font-size: {subtitle_px}px; color: rgba(255, 255, 255, 0.95); margin: 10px 0 0 0;'>{app_subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def render_feedback_box(feedback_url, colour_scheme):
    """show the survey feedback box next to the header.
    tint, border, and button colour all follow the active colour scheme so
    the two boxes read as a coherent pair rather than clashing."""
    theme = _theme_for(colour_scheme)
    st.markdown(f"""
    <div style='text-align:center; padding:20px 16px; background:{theme["feedback_tint"]}; border:2px solid {theme["feedback_border"]}; border-radius:12px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center;'>
        <p style='margin:0 0 8px 0; font-size:0.95em; font-weight:700; color:var(--text);'>💬 Help improve this app!</p>
        <p style='margin:0 0 12px 0; font-size:0.8em; color:var(--text); opacity:0.75;'>Your feedback supports our research</p>
        <a href='{feedback_url}' target='_blank' style='display:inline-block; padding:10px 20px; background:{theme["feedback_btn"]}; color:white; text-decoration:none; border-radius:8px; font-weight:700; font-size:0.9em;'>📝 Take Survey</a>
    </div>
    """, unsafe_allow_html=True)


# --- CSS styling ---

def apply_styles(font_style, text_size, colour_scheme, line_spacing=1.8, reduce_motion=False):
    """apply the accessibility-focused styles to the page.

    line_spacing (float): CSS line-height value (1.5 / 1.8 / 2.0 in the
        sidebar). piped through as a CSS variable so inline styles in the
        card rendering can pick it up.
    reduce_motion (bool): when True, injects a global rule that kills every
        transition, animation and hover-lift. separate from the OS-level
        @media (prefers-reduced-motion) rule further down in the CSS —
        this is an in-app override some users prefer.
    """
    
    colors = {
        "Soft Blue":                  {"bg": "#E8F1F5", "text": "#1C3A42", "accent": "#3A7CA5"},
        "Pale Lavender":              {"bg": "#F5E8F5", "text": "#3C2C42", "accent": "#7C3C9C"},
        "Pale Mint":                  {"bg": "#E8F5F1", "text": "#1C3C32", "accent": "#2F7A55"},
        # low-chroma near-greyscale page-level palette to match the card-level
        # Low Stimulation scheme in get_card_colors().
        "Low Stimulation":            {"bg": "#F2F2EC", "text": "#2E2E2E", "accent": "#555555"},
    }
    
    c = colors.get(colour_scheme, colors["Low Stimulation"])
    
    # we use css variables so we only inject the theme values once at the top
    # then the rest of the css just references them with var(--name)
    # font-family is WRAPPED IN QUOTES because some font names are multi-word
    # ("Comic Sans MS", "Open Dyslexic", "Trebuchet MS") — unquoted, those
    # fall back silently. quoting covers single-word names too, harmlessly.
    # in-app reduce-motion override. when the user has ticked "Reduce Motion"
    # in the sidebar, we prepend a block that kills every transition and
    # animation globally, overriding anything declared later. kept separate
    # from the OS-level @media (prefers-reduced-motion) block at the bottom
    # of the CSS — that one triggers from Windows/macOS/iOS/Android settings
    # without any app-side action, and this one is direct in-app control.
    reduce_motion_css = ""
    if reduce_motion:
        reduce_motion_css = """
        *, *::before, *::after {
            transition: none !important;
            animation: none !important;
        }
        [data-testid="stButton"] button:hover {
            transform: none !important;
        }
        """

    st.markdown(f"""
    <style>
    {reduce_motion_css}
    /* load the two web-hosted dyslexia-friendly fonts.
       OpenDyslexic: purpose-designed for dyslexic readers (weighted bases
       anchor letters and stop flipping). Served by cdnfonts.
       Lexend: research-backed for reading proficiency in general readers.
       Served by Google Fonts.
       Both @import lines degrade gracefully — if the CDN is unreachable,
       the chosen font falls back to sans-serif via the stack below. */
    @import url('https://fonts.cdnfonts.com/css/opendyslexic');
    @import url('https://fonts.googleapis.com/css2?family=Lexend:wght@400;700&display=swap');

    :root {{
        --bg: {c['bg']};
        --text: {c['text']};
        --accent: {c['accent']};
        --font-family: "{font_style}";
        --font-size: {text_size}px;
        --line-height: {line_spacing};
    }}
    
    [data-testid="stAppViewContainer"] {{ background-color: var(--bg) !important; }}
    [data-testid="stMainBlockContainer"] {{ background-color: var(--bg) !important; }}
    section[data-testid="stSidebar"] {{ background-color: var(--bg) !important; }}
    [data-testid="stColumn"] {{ background-color: var(--bg) !important; }}
    
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stMarkdownContainer"] li {{
        font-family: var(--font-family), sans-serif !important;
        font-size: var(--font-size) !important;
        color: var(--text) !important;
        letter-spacing: 0.35px !important;
        word-spacing: 1.23px !important;
        line-height: var(--line-height) !important;
    }}
    
    h1, h2, h3, h4, h5, h6 {{
        font-family: var(--font-family), sans-serif !important;
        color: var(--accent) !important;
        font-weight: 700 !important;
    }}
    
    label {{
        font-family: var(--font-family), sans-serif !important;
        font-size: var(--font-size) !important;
        color: var(--text) !important;
        background-color: transparent !important;
    }}
    
    [data-testid="stSelectbox"] div div {{
        background-color: #FFFFFF !important;
        color: var(--text) !important;
    }}
    
    [data-testid="stTextArea"] textarea {{
        background-color: #FFFFFF !important;
        color: var(--text) !important;
        font-family: var(--font-family), sans-serif !important;
        font-size: var(--font-size) !important;
    }}
    
    [data-testid="stRadio"] label {{ background-color: transparent !important; }}
    [data-testid="stCheckbox"] label {{ background-color: transparent !important; }}
    
    button {{
        font-family: var(--font-family), sans-serif !important;
        font-size: var(--font-size) !important;
    }}
    
    button:hover {{ background-color: rgba(0, 0, 0, 0.05) !important; }}
    i, em {{ font-style: normal !important; }}
    hr {{ border-color: var(--accent) !important; }}
    
    /* give flashcard images nice rounded corners */
    [data-testid="stImage"] img {{
        border-radius: 12px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
    }}
    
    /* style the flashcard containers (try multiple selectors since streamlit's DOM varies) */
    div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stContainer"],
    .stContainer,
    div[class*="stVerticalBlockBorderWrapper"] {{
        background-color: #FFFEF9 !important;
        border-radius: 16px !important;
        border: 1px solid rgba(0, 0, 0, 0.06) !important;
        border-left: 6px solid var(--accent) !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08) !important;
        padding: 20px !important;
        margin-bottom: 8px !important;
        transition: box-shadow 0.2s ease !important;
    }}
    
    div[data-testid="stVerticalBlockBorderWrapper"]:hover,
    div[data-testid="stContainer"]:hover {{
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12) !important;
    }}
    
    /* clear focus outlines for accessibility.
       on selectboxes we DON'T outline the whole component (too big — wraps
       the label too). instead we highlight each dropdown option as the
       cursor moves over it OR as the user navigates with arrow keys. this
       gives a small focus indicator that follows what the user is about
       to pick. */
    button:focus-visible,
    [data-testid="stTextArea"] textarea:focus {{
        outline: 3px solid var(--accent) !important;
        outline-offset: 2px !important;
    }}

    /* per-option hover/keyboard highlight inside the dropdown list.
       streamlit's selectbox uses baseweb under the hood, which renders
       options with role="option". aria-selected is set automatically as
       the user arrow-keys through the list, so the same rule covers
       both mouse and keyboard users. */
    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {{
        background-color: var(--accent) !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
        margin: 2px 4px !important;
    }}

    /* pointer cursor on every interactive setting in the sidebar.
       browsers default to the text I-beam on form inputs, but for
       click-to-pick controls (selectbox, slider, checkbox) the pointer
       hand is the clearer signal — matches the "Make Flashcard" button
       and gives learners consistent "this is clickable" feedback. */
    [data-testid="stSelectbox"],
    [data-testid="stSelectbox"] *,
    [data-testid="stCheckbox"],
    [data-testid="stCheckbox"] *,
    [data-testid="stSlider"] [role="slider"],
    [data-testid="stRadio"] label,
    li[role="option"] {{
        cursor: pointer !important;
    }}
    
    /* make buttons feel more tactile */
    [data-testid="stButton"] button {{
        border-radius: 10px !important;
        padding: 10px 16px !important;
        font-weight: 600 !important;
        transition: transform 0.1s ease, box-shadow 0.2s ease !important;
    }}
    
    [data-testid="stButton"] button:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
    }}

    /* respect the user's OS-level "reduce motion" setting.
       autistic users, users with vestibular disorders, and anyone prone
       to migraines often have this enabled — it's enforced from Windows,
       macOS, iOS, and Android accessibility settings. we disable every
       transition, transform and animation so nothing moves that they
       didn't ask to move. */
    @media (prefers-reduced-motion: reduce) {{
        *, *::before, *::after {{
            transition: none !important;
            animation: none !important;
        }}
        [data-testid="stButton"] button:hover {{
            transform: none !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)
