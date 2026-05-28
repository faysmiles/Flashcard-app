# utils.py - COMPLETELY FIXED (Emojis + Images + Wikipedia)
import streamlit as st
import re
import os
import requests
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

# ==================== EMOJI PICKERS ====================

# Topic emojis: matched against a single keyword (the LLM-provided topic_keyword
# or the card title). Order doesn't matter much here since titles are short.
_TOPIC_EMOJI_MAP = {
    'dog': '🐕', 'dogs': '🐕', 'puppy': '🐕', 'puppies': '🐕', 'canine': '🐕',
    'cat': '🐈', 'cats': '🐈', 'kitten': '🐈', 'feline': '🐈',
    'lion': '🦁', 'lioness': '🦁', 'tiger': '🐅',
    'elephant': '🐘', 'elephants': '🐘',
    'giraffe': '🦒', 'giraffes': '🦒',
    'whale': '🐋', 'whales': '🐋', 'dolphin': '🐬', 'dolphins': '🐬',
    'bird': '🐦', 'birds': '🐦', 'eagle': '🦅', 'owl': '🦉',
    'butterfly': '🦋', 'butterflies': '🦋',
    'bee': '🐝', 'bees': '🐝',
    'fish': '🐟', 'fishes': '🐟', 'shark': '🦈',
    'snake': '🐍', 'snakes': '🐍',
    'frog': '🐸', 'frogs': '🐸',
    'rabbit': '🐰', 'rabbits': '🐰', 'bunny': '🐰',
    'horse': '🐴', 'horses': '🐴', 'pony': '🐴',
    'cow': '🐄', 'cows': '🐄', 'bull': '🐂',
    'pig': '🐷', 'pigs': '🐷',
    'sheep': '🐑', 'lambs': '🐑',
    'goat': '🐐', 'goats': '🐐',
    'monkey': '🐒', 'monkeys': '🐒', 'ape': '🦍',
    'bear': '🐻', 'bears': '🐻',
    'panda': '🐼', 'pandas': '🐼',
    'kangaroo': '🦘', 'koala': '🐨',
    'fox': '🦊', 'deer': '🦌', 'moose': '🦌',
    'zebra': '🦓', 'hippo': '🦛', 'rhino': '🦏',
    'moon': '🌙', 'planet': '🪐', 'star': '⭐', 'sun': '☀️',
    'atom': '⚛️', 'molecule': '🧪', 'dna': '🧬', 'cell': '🔬',
    'brain': '🧠', 'heart': '❤️', 'bone': '🦴',
    'tree': '🌳', 'flower': '🌸', 'leaf': '🌿', 'plant': '🌱',
    'mountain': '⛰️', 'volcano': '🌋', 'ocean': '🌊', 'river': '🏞️',
    'rain': '🌧️', 'snow': '❄️', 'lightning': '⚡',
}


# Fact emojis: ORDERED list of (keyword-list, emoji) tuples. The picker scans
# the FULL fact text and the first match wins, so put multi-word phrases and
# more specific concepts at the top.
_FACT_EMOJI_PATTERNS = [
    # --- Multi-word phrases (must come first to beat single-word matches) ---
    (["best friend", "best friends", "man's best friend"], "🤝"),
    (["body language"], "🗣️"),
    (["sign language"], "🤟"),
    (["sense of smell"], "👃"),
    (["world war"], "⚔️"),
    (["solar system"], "🪐"),
    (["climate change", "global warming"], "🌡️"),
    (["food chain"], "🔗"),
    (["life cycle"], "🔄"),

    # --- Communication & social ---
    (["communicate", "communication", "language", "speak", "speech", "talk", "talking", "conversation"], "💬"),
    (["bark", "barking", "howl", "growl", "meow", "roar", "sound", "noise"], "🔊"),
    (["listen", "hearing", "ear"], "👂"),
    (["smell", "scent", "odor", "odour", "nose"], "👃"),
    (["see", "sight", "vision", "eye", "eyes", "watch"], "👀"),
    (["taste", "tongue", "flavour", "flavor"], "👅"),
    (["touch", "feel", "feeling"], "✋"),

    # --- Relationships ---
    (["friend", "friendship", "companion", "buddy"], "🤝"),
    (["family", "parent", "mother", "father", "child", "children"], "👨\u200d👩\u200d👧"),
    (["love", "affection", "romance"], "❤️"),
    (["enemy", "fight", "fighting", "attack", "war", "battle"], "⚔️"),
    (["pack", "group", "herd", "flock", "swarm"], "👥"),

    # --- Behaviour / actions ---
    (["mark", "marking", "territory", "claim"], "🚩"),
    (["hunt", "hunting", "predator", "prey"], "🏹"),
    (["sleep", "sleeping", "rest", "nap", "dream"], "😴"),
    (["eat", "eating", "food", "meal", "diet", "feed"], "🍽️"),
    (["drink", "drinking", "thirst"], "🥤"),
    (["urinate", "urinating", "urine", "pee", "waste"], "💧"),
    (["run", "running", "race", "sprint"], "🏃"),
    (["jump", "leap", "hop"], "🦘"),
    (["swim", "swimming", "dive"], "🏊"),
    (["fly", "flying", "flight"], "🕊️"),
    (["climb", "climbing"], "🧗"),
    (["play", "playing", "fun", "game"], "🎮"),
    (["learn", "learning", "study", "school", "education"], "🎓"),
    (["work", "working", "job", "labour", "labor"], "💼"),
    (["build", "building", "construct"], "🏗️"),
    (["protect", "protection", "guard", "defend", "defense", "defence"], "🛡️"),

    # --- Body parts ---
    (["tail", "wag", "wagging"], "〰️"),
    (["paw", "paws", "claw", "claws"], "🐾"),
    (["fur", "coat", "hair"], "🧴"),
    (["teeth", "tooth", "fang", "fangs", "bite"], "🦷"),
    (["wing", "wings", "feather", "feathers"], "🪶"),

    # --- Numbers, size, time ---
    (["million", "billion", "thousand", "many", "lots"], "🔢"),
    (["big", "large", "huge", "giant", "enormous"], "📏"),
    (["small", "tiny", "little", "miniature"], "🔍"),
    (["fast", "quick", "speed", "rapid"], "⚡"),
    (["slow", "slowly"], "🐢"),
    (["old", "ancient", "history", "historical", "past"], "📜"),
    (["new", "modern", "recent", "today"], "✨"),
    (["year", "years", "century", "decade", "day", "days", "month", "months", "week", "weeks", "hour", "hours", "minute", "minutes", "second", "seconds"], "📅"),

    # --- Space / motion ---
    (["orbit", "orbits", "orbiting", "revolve", "rotate", "rotation"], "🔄"),
    (["walk", "walked", "walking", "step"], "🚶"),
    (["travel", "travels", "journey", "voyage"], "🧭"),
    (["reflect", "reflects", "reflection", "mirror"], "🪞"),
    (["discover", "discovered", "discovery", "explore"], "🔭"),

    # --- Habitat / environment ---
    (["forest", "wood", "woods", "jungle"], "🌳"),
    (["desert", "sand", "dune"], "🏜️"),
    (["arctic", "polar", "ice", "frozen"], "🧊"),
    (["sea", "ocean", "marine"], "🌊"),
    (["mountain", "hill"], "⛰️"),
    (["sky", "cloud", "clouds"], "☁️"),
    (["home", "house", "shelter", "den", "nest"], "🏠"),
    (["city", "urban", "town"], "🏙️"),
    (["farm", "rural", "countryside"], "🚜"),

    # --- Science / abstract ---
    (["energy", "power", "electric", "electricity"], "⚡"),
    (["water", "liquid", "wet"], "💧"),
    (["fire", "flame", "burn", "hot"], "🔥"),
    (["cold", "freeze", "freezing"], "❄️"),
    (["light", "bright", "shine"], "💡"),
    (["dark", "darkness", "shadow", "night"], "🌑"),
    (["health", "healthy", "medicine", "medical", "doctor"], "🩺"),
    (["disease", "illness", "sick", "infection", "virus", "bacteria"], "🦠"),
    (["danger", "dangerous", "risk", "warning"], "⚠️"),
    (["safe", "safety", "secure"], "🛡️"),
    (["money", "cost", "price", "economy", "trade"], "💰"),
    (["important", "essential", "key", "main"], "⭐"),
    (["idea", "thought", "concept", "theory"], "💡"),
    (["question", "ask", "wonder"], "❓"),
    (["answer", "solve", "solution"], "✅"),

    # --- Generic entities (catch-all, comes after concepts) ---
    (["dog", "puppy", "canine"], "🐕"),
    (["cat", "kitten", "feline"], "🐈"),
    (["human", "people", "person", "man", "woman"], "🧑"),
    (["plant", "tree", "flower"], "🌿"),
    (["bird"], "🐦"),
    (["fish"], "🐟"),
]


def get_emoji_for_topic(text):
    """Pick an emoji for a card TOPIC (short string like 'Dogs as Pets')."""
    if not text:
        return '📚'
    text_lower = text.lower()
    for keyword, emoji in _TOPIC_EMOJI_MAP.items():
        if keyword in text_lower:
            return emoji
    return '📚'


def pick_fact_emoji(fact_text, fallback='✨'):
    """Pick an emoji based on KEYWORDS inside the fact text itself.

    Scans the full sentence for concept words (mark, communicate, friend, etc.)
    so each fact on a card gets a distinct, content-relevant icon instead of
    all sharing the topic emoji. Uses word-boundary matching so short keywords
    like 'ear' don't match inside 'Earth'.
    """
    if not fact_text:
        return fallback
    text_lower = fact_text.lower()
    for keywords, emoji in _FACT_EMOJI_PATTERNS:
        for kw in keywords:
            # Word-boundary match; supports multi-word phrases.
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, text_lower):
                return emoji
    return fallback


# ==================== BETTER IMAGE SEARCH WITH WIKIPEDIA BACKUP ====================

@st.cache_data(show_spinner=False, ttl=3600)
def search_wikipedia_image(query):
    """Search Wikipedia for images - MULTIPLE FALLBACKS"""
    if not query:
        return None
    
    clean_query = re.sub(r'[^\w\s-]', '', query).strip()
    if not clean_query:
        return None
    
    # List of API endpoints to try (multiple fallbacks)
    search_terms = [
        clean_query,
        clean_query.split()[0] if len(clean_query.split()) > 1 else clean_query,
        clean_query + " species" if "dog" in clean_query.lower() or "cat" in clean_query.lower() else clean_query,
    ]
    
    for term in search_terms[:3]:  # Try up to 3 variations
        try:
            # Try direct page first
            params = {
                "action": "query",
                "format": "json",
                "titles": term,
                "prop": "pageimages",
                "piprop": "thumbnail",
                "pithumbsize": 500,
            }
            
            response = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params=params,
                timeout=8,
                headers={"User-Agent": "FlashcardMagic/1.0 (educational; contact@example.com)"}
            )
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    if "thumbnail" in page_data and int(page_id) > 0:
                        img_url = page_data["thumbnail"]["source"]
                        if img_url and not any(x in page_data.get("title", "").lower() for x in ['disambiguation', 'list of']):
                            return img_url
            
            # Try search if direct failed
            params = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": term,
                "gsrlimit": 10,
                "prop": "pageimages",
                "piprop": "thumbnail",
                "pithumbsize": 500,
            }
            
            response = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params=params,
                timeout=8,
                headers={"User-Agent": "FlashcardMagic/1.0"}
            )
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get("query", {}).get("pages", {})
                
                # Sort by relevance (page ID positive)
                valid_pages = []
                for page_id, page_data in pages.items():
                    if "thumbnail" in page_data and int(page_id) > 0:
                        title = page_data.get("title", "").lower()
                        # Skip disambiguation pages
                        if not any(bad in title for bad in ['disambiguation', 'list of', '(disambiguation)']):
                            valid_pages.append(page_data)
                
                # Return the best match (first one)
                for page_data in valid_pages:
                    if "thumbnail" in page_data:
                        return page_data["thumbnail"]["source"]
        
        except Exception as e:
            print(f"Wikipedia search error for '{term}': {str(e)}")
            continue
    
    # Special fallback for common animals - use direct known image URLs
    animal_fallbacks = {
        'dog': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Golden_Retriever_Dukedog_Clipping.jpg/500px-Golden_Retriever_Dukedog_Clipping.jpg',
        'cat': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/500px-Cat03.jpg',
        'lion': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Lion_waiting_in_Namibia.jpg/500px-Lion_waiting_in_Namibia.jpg',
        'elephant': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/bf/African_Bush_Elephant.jpg/500px-African_Bush_Elephant.jpg',
        'giraffe': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Giraffe_Mikumi_National_Park.jpg/500px-Giraffe_Mikumi_National_Park.jpg',
        'butterfly': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Monarch_Butterfly_Danaus_plexippus.jpg/500px-Monarch_Butterfly_Danaus_plexippus.jpg',
    }
    
    for key, url in animal_fallbacks.items():
        if key in clean_query.lower():
            return url
    
    return None


# ==================== DEEPSEEK FLASHCARD GENERATION ====================

@st.cache_data(show_spinner=False, ttl=3600)
def _fetch_flashcard_data_from_llm(raw_text, reading_level="intermediate"):
    """Call DeepSeek and return the raw parsed flashcard list (cached).

    Kept separate from enrichment so changing the emoji map doesn't require
    a cache flush - only the API call itself is memoised.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["DEEPSEEK_API_KEY"]
        except Exception:
            st.error("🔑 Missing DeepSeek API key")
            st.info("Add your key to .env or Streamlit secrets")
            return None

    # Scale card count
    n_chars = len(raw_text)
    if n_chars <= 8000:
        min_cards, max_cards = 3, 5
    elif n_chars <= 16000:
        min_cards, max_cards = 5, 8
    else:
        min_cards, max_cards = 8, 12

    # Reading level instructions
    if reading_level == "simple":
        level_text = "VERY SIMPLE: Use short words, short sentences (8-12 words max)"
    elif reading_level == "complex":
        level_text = "ADVANCED: Use precise academic language, longer sentences (up to 25 words)"
    else:
        level_text = "MEDIUM: Clear everyday language, medium sentences (12-18 words)"

    # Updated prompt: ask the LLM for a UNIQUE keyword per fact reflecting that
    # fact's content (not the card topic). Example shows varied hints.
    prompt = f"""Create {min_cards}-{max_cards} flashcards from this text.

READING LEVEL: {level_text}

IMPORTANT RULES:
- Each fact must have an "emoji_hint" which is ONE keyword describing what THAT
  specific fact is about (an action, concept, or object from the sentence).
- Do NOT just repeat the card topic in every emoji_hint - vary it per fact.
- For dog-related content, use 🐕; for cats use 🐈.
- Return ONLY valid JSON.

Example format (note how emoji_hint differs per fact):
{{
  "flashcards": [
    {{
      "title": "Dogs as Pets",
      "topic_keyword": "dog",
      "image_search": "dog",
      "facts": [
        {{"text": "Dogs mark their territory by urinating.", "emoji_hint": "territory"}},
        {{"text": "Dogs use body language to communicate.", "emoji_hint": "communicate"}},
        {{"text": "Dogs are known as man's best friend.", "emoji_hint": "best friend"}}
      ]
    }}
  ]
}}

TEXT:
{raw_text[:15000]}"""

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You create flashcards. Each fact's emoji_hint is a unique keyword reflecting that fact's specific content - never just the topic. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        content = response.choices[0].message.content
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        result = json.loads(content)
        return result.get("flashcards", [])

    except json.JSONDecodeError as e:
        st.error(f"JSON parsing error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"API error: {str(e)}")
        return None


def generate_flashcards_from_llm(raw_text, reading_level="intermediate"):
    """Generate flashcards: cached LLM call + fresh emoji enrichment per fact.

    The emoji for each fact is picked from the FACT TEXT (not just the LLM's
    hint), so each bullet on a card reflects its own content.
    """
    raw_data = _fetch_flashcard_data_from_llm(raw_text, reading_level)
    if not raw_data:
        if raw_data is None:
            return None
        st.error("No flashcards generated")
        return None

    flashcards = []
    for card in raw_data:
        topic = card.get("title", "")
        topic_keyword = card.get("topic_keyword", topic)
        topic_emoji = get_emoji_for_topic(topic_keyword or topic)

        facts = []
        for fact in card.get("facts", [])[:4]:
            if isinstance(fact, dict):
                fact_text = fact.get("text", "")
                emoji_hint = fact.get("emoji_hint", "")
                # 1) Try the fact text itself (most accurate - matches concept words).
                # 2) Try the LLM's hint if the text didn't match.
                # 3) Fall back to the topic emoji (always relevant, never just '📚').
                fact_emoji = pick_fact_emoji(fact_text, fallback=None)
                if fact_emoji is None and emoji_hint:
                    fact_emoji = pick_fact_emoji(emoji_hint, fallback=None)
                if fact_emoji is None:
                    fact_emoji = topic_emoji
                facts.append({"emoji": fact_emoji, "text": fact_text})
            elif isinstance(fact, str):
                fact_emoji = pick_fact_emoji(fact, fallback=topic_emoji)
                facts.append({"emoji": fact_emoji, "text": fact})

        flashcards.append({
            'title': topic,
            'facts': facts,
            'emoji': topic_emoji,
            'image_search': card.get('image_search', topic_keyword),
        })

    return flashcards


# ==================== EXISTING HELPER FUNCTIONS (keep these) ====================

def get_card_colors(colour_scheme):
    """Derive card colours (text/label/accent) from the shared COLOR_SCHEMES table.

    Single source of truth: config.COLOR_SCHEMES. Adding a new scheme there
    automatically makes it work here.
    """
    palette = _get_scheme_palette(colour_scheme)
    return {
        "text": palette["text"],
        "label": palette["accent"],
        "accent": palette["accent"],
        "card_bg": palette["card_bg"],
    }


def extract_text_from_file(uploaded_file):
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
        elif "wordprocessingml" in uploaded_file.type:
            from docx import Document
            doc = Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
        else:
            return "Unsupported file type"
    except Exception as e:
        return f"Error: {str(e)}"


def fetch_image_bytes(url):
    if not url:
        return None
    try:
        r = requests.get(url, headers={"User-Agent": "FlashcardMagic/1.0"}, timeout=10)
        if r.ok:
            return r.content
    except:
        pass
    return None


def render_card_to_png(card, colors, idx, total, wiki_image_bytes=None, page_bg_hex="#F5F1E8"):
    """Simple PNG render that respects the chosen colour scheme."""
    W = 700
    MARGIN = 30

    card_bg = colors.get("card_bg", "#FFFFFF")

    img = Image.new("RGB", (W, 500), page_bg_hex)
    draw = ImageDraw.Draw(img)

    # Card background (respects dark/high-contrast schemes)
    draw.rectangle([MARGIN, MARGIN, W-MARGIN, 470], fill=card_bg, outline=colors['accent'], width=3)
    
    # Title
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 18)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Center title
    bbox = draw.textbbox((0, 0), card['title'], font=font)
    text_width = bbox[2] - bbox[0]
    draw.text(((W - text_width) // 2, 100), card['title'], fill=colors['text'], font=font)
    
    # Draw facts
    y = 180
    for fact in card['facts'][:3]:
        text = fact.get('text', '')[:100]
        emoji = fact.get('emoji', '•')
        draw.text((MARGIN + 20, y), f"{emoji} {text}", fill=colors['text'], font=small_font)
        y += 45
    
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def build_cards_zip(flashcards, card_images, colors, page_bg_hex, cache_key):
    import zipfile
    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, card in enumerate(flashcards[:10]):
            img_bytes = fetch_image_bytes(card_images.get(i))
            png = render_card_to_png(card, colors, i, len(flashcards), img_bytes, page_bg_hex)
            safe_title = re.sub(r'[^a-zA-Z0-9_-]+', '_', card['title'])[:30]
            zf.writestr(f"card_{i+1}_{safe_title}.png", png)
    return zip_buf.getvalue()


def render_header(app_title, app_subtitle, text_size, colour_scheme):
    st.markdown(f"""
    <div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #2C5282, #3182CE); border-radius: 12px; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0; font-size: {text_size * 2}px;'>💡 {app_title}</h1>
        <p style='color: rgba(255,255,255,0.9); margin: 10px 0 0 0;'>{app_subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def render_feedback_box(feedback_url, colour_scheme):
    st.markdown(f"""
    <div style='text-align: center; padding: 20px; margin-top: 40px; border-top: 1px solid #ddd;'>
        <p>💬 Help improve this app! <a href='{feedback_url}' target='_blank'>Take Survey</a></p>
    </div>
    """, unsafe_allow_html=True)


def render_mobile_settings_hint():
    st.markdown("""
    <div style='background: #f0f0f0; padding: 10px; border-radius: 8px; margin-bottom: 15px; text-align: center; font-size: 14px;'>
        ⚙️ Tap the <strong>☰</strong> icon in the top-left to access settings!
    </div>
    """, unsafe_allow_html=True)


def _get_scheme_palette(colour_scheme):
    """Look up a scheme by name across all groups in COLOR_SCHEMES."""
    from config import COLOR_SCHEMES
    for group in COLOR_SCHEMES.values():
        if colour_scheme in group:
            return group[colour_scheme]
    # Fallback - Soft Blue
    return COLOR_SCHEMES["Accessibility"]["Soft Blue"]


def apply_styles(font_style, text_size, colour_scheme, line_spacing=1.8):
    """Inject CSS for the chosen scheme - paints page bg, sidebar, text, inputs.

    Streamlit's config.toml sets the initial theme once at boot; this function
    overrides it at runtime so changing the dropdown actually re-paints.
    """
    palette = _get_scheme_palette(colour_scheme)
    bg = palette["bg"]
    text = palette["text"]
    accent = palette["accent"]
    card_bg = palette["card_bg"]

    # Sidebar: a slightly different shade so it reads as a separate panel.
    # Use card_bg for dark schemes, white-ish for light schemes.
    is_dark = bg.lower() in ("#000000", "#0d1b2a", "#0a0a0a")
    sidebar_bg = card_bg if is_dark else "#FFFFFF"
    input_bg = card_bg if is_dark else "#FFFFFF"
    border_col = accent if is_dark else "rgba(0,0,0,0.12)"

    st.markdown(f"""
    <style>
    /* Font + base sizing */
    html, body, [class*="css"] {{
        font-family: '{font_style}', sans-serif !important;
    }}
    p, li, label, .stMarkdown {{
        font-size: {text_size}px !important;
        line-height: {line_spacing} !important;
        color: {text};
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: {text} !important;
        font-family: '{font_style}', sans-serif !important;
    }}

    /* Page background */
    .stApp, [data-testid="stAppViewContainer"] {{
        background-color: {bg} !important;
        color: {text} !important;
    }}
    [data-testid="stHeader"] {{
        background-color: {bg} !important;
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg} !important;
    }}
    [data-testid="stSidebar"] * {{
        color: {text} !important;
    }}

    /* Inputs, selects, textareas */
    .stTextInput input, .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div,
    .stNumberInput input {{
        background-color: {input_bg} !important;
        color: {text} !important;
        border: 1px solid {border_col} !important;
    }}

    /* Radio + checkbox labels */
    .stRadio label, .stCheckbox label {{
        color: {text} !important;
    }}

    /* Captions */
    .stCaption, [data-testid="stCaptionContainer"] {{
        color: {text} !important;
        opacity: 0.75;
    }}

    /* Buttons - use accent colour */
    .stButton button {{
        border-radius: 10px !important;
        padding: 10px 20px !important;
        font-weight: bold !important;
        background-color: {accent} !important;
        color: {card_bg if is_dark else "#FFFFFF"} !important;
        border: 1px solid {accent} !important;
    }}
    .stButton button:hover {{
        opacity: 0.9;
        filter: brightness(1.05);
    }}
    .stButton button:disabled {{
        opacity: 0.4;
    }}

    /* Download buttons match */
    .stDownloadButton button {{
        background-color: {accent} !important;
        color: {card_bg if is_dark else "#FFFFFF"} !important;
        border: 1px solid {accent} !important;
        border-radius: 10px !important;
        font-weight: bold !important;
    }}

    /* File uploader */
    [data-testid="stFileUploader"] section {{
        background-color: {input_bg} !important;
        border: 1px dashed {border_col} !important;
    }}

    /* Slider track */
    .stSlider [data-baseweb="slider"] div[role="slider"] {{
        background-color: {accent} !important;
    }}
    </style>
    """, unsafe_allow_html=True)
