# utils.py - COMPLETELY FIXED (Emojis + Images + Wikipedia)
import streamlit as st
import re
import os
import requests
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
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
    (["fur", "coat", "fleece", "wool", "pelage"], "🐑"),
    (["hair", "mane", "bristle"], "💇"),
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


# ==================== AI IMAGE GENERATION VIA POLLINATIONS ====================


def _looks_like_emoji(s):
    """Best-effort check that a short string is an emoji (not text/ascii).
    Accepts single emoji plus modifiers/ZWJ sequences. No external library.
    """
    if not s or not isinstance(s, str):
        return False
    s = s.strip()
    if not s or len(s) > 8:
        return False
    # Reject anything containing ascii letters/digits (i.e. plain text)
    if any(c.isascii() and c.isalnum() for c in s):
        return False
    # Require at least one char in a pictographic/emoji range
    for c in s:
        o = ord(c)
        if (0x1F000 <= o <= 0x1FAFF) or (0x2600 <= o <= 0x27BF) \
           or (0x2190 <= o <= 0x21FF) or (0x2B00 <= o <= 0x2BFF) \
           or o in (0x2122, 0x2139) or (0x1F1E6 <= o <= 0x1F1FF) \
           or (0xFE00 <= o <= 0xFE0F) or (0x2700 <= o <= 0x27BF):
            return True
    return False

# ==================== TWEMOJI: CRISP, IDENTICAL EMOJIS EVERYWHERE ====================
# Converts emoji characters in a string into <img> tags pointing at the Twemoji
# SVG set (served via jsDelivr). This makes every emoji render identically and
# sharply on all devices, instead of using each device's own system font.
# The original emoji is kept in the img alt, so it still degrades gracefully.

_TWEMOJI_CDN = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/svg"

# Matches single emoji, skin-tone modifiers, variation selectors, flags, keycaps
# and ZWJ sequences (e.g. family emoji) as one unit.
_EMOJI_RE = re.compile(
    "(?:"
    "[#*0-9]\uFE0F?\u20E3"
    "|[\U0001F1E6-\U0001F1FF]{2}"
    "|[\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U00002190-\U000021FF"
    "\U00002300-\U000023FF"
    "\u2122\u2139\u3030\u303D\u3297\u3299\u00A9\u00AE]"
    "[\U0001F3FB-\U0001F3FF]?"
    "\uFE0F?"
    "(?:\u200D"
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF]"
    "[\U0001F3FB-\U0001F3FF]?\uFE0F?)*"
    ")"
)


def _twemoji_codepoint(emoji):
    """Build the Twemoji filename codepoint for an emoji cluster.
    Mirrors Twemoji's own rule: strip the variation selector (FE0F) unless the
    cluster contains a zero-width joiner (ZWJ), then join codepoints with '-'.
    """
    if "\u200d" not in emoji:
        emoji = emoji.replace("\ufe0f", "")
    return "-".join(f"{ord(c):x}" for c in emoji)


def twemojify(text, size="1em"):
    """Replace emoji in text with Twemoji <img> tags. size sets the rendered
    height/width (defaults to 1em so it scales with the surrounding font size).
    """
    if not text:
        return text

    def _replace(match):
        emoji = match.group(0)
        code = _twemoji_codepoint(emoji)
        src = f"{_TWEMOJI_CDN}/{code}.svg"
        return (
            f"<img class='twemoji' src='{src}' alt='{emoji}' draggable='false' "
            f"style='height:{size}; width:{size}; margin:0 .08em; "
            f"vertical-align:-0.15em; display:inline-block;' loading='lazy' />"
        )

    return _EMOJI_RE.sub(_replace, text)


def _get_pollinations_key():
    try:
        return st.secrets.get("POLLINATIONS_API_KEY") or os.getenv("POLLINATIONS_API_KEY")
    except Exception:
        return os.getenv("POLLINATIONS_API_KEY")


# ==================== SUPABASE IMAGE CACHE (durable, shared across users) ====================
# A generated image is saved to Supabase storage and indexed by its keyword.
# The next user who needs the SAME keyword gets the stored image instantly,
# with no new generation. The cache fills up and gets more useful over time.
# This layer is OPTIONAL: if the Supabase secrets are not set, image generation
# works exactly as before (generate fresh each time).

_IMAGE_BUCKET = "flashcard-images"


@st.cache_resource(show_spinner=False)
def _get_supabase():
    """Return a cached Supabase client, or None if not configured."""
    try:
        try:
            url = st.secrets.get("SUPABASE_URL")
            key = st.secrets.get("SUPABASE_KEY")
        except Exception:
            url = key = None
        url = url or os.getenv("SUPABASE_URL")
        key = key or os.getenv("SUPABASE_KEY")
        if not url or not key:
            return None
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        print(f"Supabase init skipped: {e}")
        return None


def _normalise_keyword(text):
    """Lowercase, strip punctuation, collapse spaces - so 'Dogs ' and 'dogs'
    map to the same cache entry. Exact match only (no stemming)."""
    cleaned = re.sub(r"[^\w\s-]", "", text or "").lower()
    return re.sub(r"\s+", " ", cleaned).strip()


def _cache_lookup(keyword):
    """Return a stored image URL for this exact keyword, or None."""
    sb = _get_supabase()
    if not sb or not keyword:
        return None
    try:
        res = (sb.table("image_cache")
                 .select("image_url")
                 .eq("keyword", keyword)
                 .limit(1)
                 .execute())
        if res.data:
            return res.data[0]["image_url"]
    except Exception as e:
        print(f"Cache lookup error for '{keyword}': {e}")
    return None


def _cache_store(keyword, image_bytes, mime):
    """Upload the image to storage and index it by keyword. Returns the public
    URL, or None on failure (caller then falls back to a data URL)."""
    sb = _get_supabase()
    if not sb or not keyword:
        return None
    try:
        ext = "png" if "png" in mime else "jpg"
        safe = re.sub(r"[^a-z0-9_-]+", "_", keyword).strip("_") or "image"
        path = f"{safe}.{ext}"
        sb.storage.from_(_IMAGE_BUCKET).upload(
            path, image_bytes,
            {"content-type": mime, "upsert": "true"},
        )
        public_url = sb.storage.from_(_IMAGE_BUCKET).get_public_url(path)
        sb.table("image_cache").upsert(
            {"keyword": keyword, "image_url": public_url}
        ).execute()
        return public_url
    except Exception as e:
        print(f"Cache store error for '{keyword}': {e}")
        return None


@st.cache_data(show_spinner=False, ttl=3600)
def search_wikipedia_image(query):
    """Return an image URL for the topic query.
    Order: durable Supabase cache (exact keyword) -> generate via Pollinations,
    then save to the cache for everyone else. Kept the original function name
    so app.py needs no changes.
    """
    if not query:
        return None

    keyword = _normalise_keyword(query)
    if not keyword:
        return None

    # 1) Durable shared cache - instant reuse if anyone made this before.
    cached = _cache_lookup(keyword)
    if cached:
        return cached

    # 2) Generate a fresh image.
    api_key = _get_pollinations_key()
    if not api_key:
        return None

    prompt = (
        f"clean educational illustration of {keyword}, "
        "simple background, suitable for children and students, "
        "bright clear colours, no text"
    )

    try:
        import urllib.parse
        import base64
        encoded = urllib.parse.quote(prompt)
        url = f"https://gen.pollinations.ai/image/{encoded}?model=flux&key={api_key}&width=500&height=500&nologo=true"
        response = requests.get(url, timeout=30)
        if response.ok and response.headers.get("content-type", "").startswith("image"):
            mime = response.headers.get("content-type", "image/jpeg").split(";")[0]
            # 3) Save to the shared cache; return the public URL if it worked.
            public_url = _cache_store(keyword, response.content, mime)
            if public_url:
                return public_url
            # Fallback: no cache configured / upload failed - use a data URL.
            b64 = base64.b64encode(response.content).decode()
            return f"data:{mime};base64,{b64}"
    except Exception as e:
        print(f"Pollinations error for '{keyword}': {e}")

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

    # Scale card count to text length
    n_chars = len(raw_text)
    if n_chars <= 5000:
        min_cards, max_cards = 3, 5
    elif n_chars <= 12000:
        min_cards, max_cards = 5, 10
    elif n_chars <= 20000:
        min_cards, max_cards = 8, 15
    else:
        min_cards, max_cards = 12, 20

    # Reading level instructions
    if reading_level == "simple":
        level_text = (
            "EASY (Ages 4-11): Use very short, common words only. "
            "One idea per sentence. Maximum 10 words per sentence. "
            "Active voice always. Use digits for numbers (e.g. 3 not three). "
            "No jargon — if a technical word is essential, explain it in the same sentence."
        )
    elif reading_level == "complex":
        level_text = (
            "ADVANCED (Ages 18+): Use precise academic vocabulary. "
            "Sentences up to 25 words. Include technical terms where appropriate. "
            "Active voice preferred. Digits for numbers. No double negatives."
        )
    else:
        level_text = (
            "MEDIUM (Ages 11-18): Clear everyday language. "
            "One idea per sentence, 12-18 words max. Active voice. "
            "Digits for numbers. Avoid jargon unless explained."
        )

    prompt = f"""You are creating educational flashcards for students with dyslexia, ADHD, and other learning differences.

READING LEVEL: {level_text}

YOUR GOAL: Turn ALL key information from the text into {min_cards}-{max_cards} flashcards that work as a quick study summary.
- Group related ideas into clearly themed cards (e.g. "How Dogs Communicate", "What Dogs Eat").
- Every distinct topic or concept in the text must appear on at least one card — do not skip anything.
- Each card has 3-5 facts. Order the facts so the MOST important or memorable one comes first.
- Each fact must be a genuine key takeaway worth remembering — not filler, not an example, not trivia.
- Give each card a short, descriptive title that captures its theme at a glance.

WRITING RULES (follow strictly):
- Active voice: write "Dogs use smell to communicate." NOT "Smell is used by dogs."
- One idea per sentence — never join 2 facts with "and" or "but".
- Front-load the key word: start the sentence with what the fact is actually about.
- Use digits for numbers: "3 types" not "three types".
- No double negatives.
- No vague openers like "It is important to note..." — start with the subject.
- Each fact must make sense on its own without reading the others.
- Keep facts tight: a clear summary sentence, not a long explanation.

EMOJI (very important — this app relies on visual cues):
- Each fact needs an "emoji": the SINGLE best emoji that represents that fact's MAIN idea.
- Choose it for meaning, not for a stray word. "Whales migrate each year" -> the journey, not the animal.
- Pick concrete, instantly recognisable emojis. Vary them across the facts on a card.
- Also include an "emoji_hint": one keyword for that fact (used as a backup).

Return ONLY valid JSON in this exact format, no commentary:
{{
  "flashcards": [
    {{
      "title": "How Dogs Communicate",
      "topic_keyword": "dog",
      "image_search": "dog communication",
      "facts": [
        {{"text": "Dogs use body language to show how they feel.", "emoji": "🗣️", "emoji_hint": "body language"}},
        {{"text": "A wagging tail usually means a dog is happy.", "emoji": "〰️", "emoji_hint": "tail"}},
        {{"text": "Dogs growl to warn others to stay away.", "emoji": "🔊", "emoji_hint": "growl"}}
      ]
    }}
  ]
}}

TEXT TO CONVERT:
{raw_text[:30000]}"""

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You create flashcards. For each fact you choose the single best emoji representing its main idea, and order the facts with the most important first. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=8000
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
        for fact in card.get("facts", [])[:5]:
            if isinstance(fact, dict):
                fact_text = fact.get("text", "")
                emoji_hint = fact.get("emoji_hint", "")
                llm_emoji = fact.get("emoji", "")
                # 1) Trust the LLM's chosen emoji if it is a real emoji - it
                #    understands the sentence's MEANING, not just its keywords.
                # 2) Else match keywords in the fact text (curated fallback).
                # 3) Else match the LLM's keyword hint.
                # 4) Else fall back to the topic emoji (always relevant).
                if _looks_like_emoji(llm_emoji):
                    fact_emoji = llm_emoji.strip()
                else:
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
        if url.startswith("data:"):
            import base64
            header, data = url.split(",", 1)
            return base64.b64decode(data)
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


# ==================== COLOUR / THEME HELPERS ====================

def _get_scheme_palette(colour_scheme):
    """Look up a scheme by name across all groups in COLOR_SCHEMES."""
    from config import COLOR_SCHEMES
    for group in COLOR_SCHEMES.values():
        if colour_scheme in group:
            return group[colour_scheme]
    # Fallback - Soft Blue
    return COLOR_SCHEMES["Accessibility"]["Soft Blue"]


def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _relative_luminance(hex_color):
    """WCAG relative luminance (0 = black, 1 = white)."""
    def chan(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _hex_to_rgb(hex_color)
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def _is_dark(hex_color):
    """True if a colour is dark enough to need light text on top of it."""
    return _relative_luminance(hex_color) < 0.4


def _contrast_ratio(fg_hex, bg_hex):
    """WCAG contrast ratio between two colours (1 = none, 21 = max)."""
    l1 = _relative_luminance(fg_hex)
    l2 = _relative_luminance(bg_hex)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _on_color(bg_hex):
    """Return black or white - whichever has the HIGHER contrast on bg_hex.

    Uses true contrast ratios, not a luminance threshold, so mid-tone colours
    (orange, teal, yellow) correctly get black text instead of low-contrast white.
    """
    return "#000000" if _contrast_ratio("#000000", bg_hex) >= _contrast_ratio("#FFFFFF", bg_hex) else "#FFFFFF"


def _best_text_color(*bg_hexes):
    """Pick black or white maximising the WORST-CASE contrast across all bgs.

    For a gradient banner, pass both gradient stops so the chosen text colour
    stays readable along the entire banner, not just at one end.
    """
    black_min = min(_contrast_ratio("#000000", bg) for bg in bg_hexes)
    white_min = min(_contrast_ratio("#FFFFFF", bg) for bg in bg_hexes)
    return "#000000" if black_min >= white_min else "#FFFFFF"


def _mix(hex_color, target_hex, amount):
    """Blend hex_color toward target_hex by `amount` (0-1). Used for shading."""
    r1, g1, b1 = _hex_to_rgb(hex_color)
    r2, g2, b2 = _hex_to_rgb(target_hex)
    r = round(r1 + (r2 - r1) * amount)
    g = round(g1 + (g2 - g1) * amount)
    b = round(b1 + (b2 - b1) * amount)
    return f"#{r:02X}{g:02X}{b:02X}"


def _header_colors(colour_scheme):
    """Single source of truth for the header banner colours.

    Returns (accent, grad_end, title_color, subtitle_color). The gradient is
    shaded AWAY from the chosen text colour so contrast stays high across the
    whole banner. Used by both render_header (to draw the banner) and
    apply_styles (to emit the high-specificity colour rules that actually win).
    """
    palette = _get_scheme_palette(colour_scheme)
    accent = palette["accent"]
    title_color = _on_color(accent)
    if title_color == "#000000":
        grad_end = _mix(accent, "#FFFFFF", 0.14)   # lighten -> black text stays dark-on-light
        subtitle_color = "rgba(0,0,0,0.82)"
    else:
        grad_end = _mix(accent, "#000000", 0.22)   # darken  -> white text stays light-on-dark
        subtitle_color = "rgba(255,255,255,0.92)"
    return accent, grad_end, title_color, subtitle_color


def _star_color(colour_scheme):
    """A colourful star tone that 'suits' the scheme: a lightness-shifted tint
    of the scheme's own accent (same hue family). Paired with a title-colour
    outline in CSS so it stays visible on any banner. Low Stimulation gets none.
    """
    accent, _grad_end, title_color, _sub = _header_colors(colour_scheme)
    if title_color == "#FFFFFF":          # dark/saturated banner -> light tint pops
        return _mix(accent, "#FFFFFF", 0.55)
    return _mix(accent, "#000000", 0.42)  # lighter banner -> deeper shade pops


def _cute_star_svg_markup():
    """Option A kawaii star: gold body, sparkly eyes, smile, rosy cheeks."""
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='-72 -72 144 144'>"
        "<polygon points='0,-60 15.3,-21 57.1,-18.5 24.7,8 35.3,48.5 0,26 "
        "-35.3,48.5 -24.7,8 -57.1,-18.5 -15.3,-21' fill='#FFD93B' "
        "stroke='#F0B400' stroke-width='9' stroke-linejoin='round'/>"
        "<ellipse cx='-15' cy='-8' rx='6.5' ry='9' fill='#3A2E2E'/>"
        "<ellipse cx='15' cy='-8' rx='6.5' ry='9' fill='#3A2E2E'/>"
        "<circle cx='-12.5' cy='-11' r='2.4' fill='#ffffff'/>"
        "<circle cx='17.5' cy='-11' r='2.4' fill='#ffffff'/>"
        "<path d='M -12 6 Q 0 20 12 6' fill='none' stroke='#3A2E2E' "
        "stroke-width='3.5' stroke-linecap='round'/>"
        "<ellipse cx='-27' cy='6' rx='7' ry='4.5' fill='#FF9EB5'/>"
        "<ellipse cx='27' cy='6' rx='7' ry='4.5' fill='#FF9EB5'/>"
        "</svg>"
    )


def _cute_star_img(size="1em", cls=""):
    """Render the kawaii star as an <img> (data-URI SVG) so it always shows in
    Streamlit. The element itself is animated by CSS in apply_styles()."""
    import urllib.parse
    uri = "data:image/svg+xml;utf8," + urllib.parse.quote(_cute_star_svg_markup())
    return (
        f"<img class='fcm-star-svg {cls}' src=\"{uri}\" alt='' aria-hidden='true' "
        f"style='height:{size}; width:{size}; vertical-align:-0.15em; "
        f"display:inline-block;' />"
    )


def render_header(app_title, app_subtitle, text_size, colour_scheme):
    """Header banner tinted to match the active scheme's accent colour.

    NOTE: the title/subtitle/star colours are NOT set reliably inline here.
    Streamlit's HTML sanitizer strips `!important` from inline style attributes,
    so an inline colour loses to the global `.stApp h1 { color: text !important }`
    rule - which paints the title in the body-text colour. On the High Contrast
    schemes that colour equals the banner background, making the title invisible.
    The real colours are applied by apply_styles() via `.fcm-header` class
    selectors inside a <style> block (where !important IS preserved) with higher
    specificity than the blanket rule. The inline colours below are a harmless
    fallback for the brief moment before the stylesheet loads.

    Decorative stars flank the title on every scheme EXCEPT Low Stimulation,
    which stays clean to reduce visual clutter for sensory-sensitive users.
    """
    accent, grad_end, title_color, subtitle_color = _header_colors(colour_scheme)

    if colour_scheme == "Low Stimulation":
        left_stars = right_stars = ""
    else:
        left_stars = (
            _cute_star_img("0.7em", "fcm-star-b")
            + _cute_star_img("1.05em", "fcm-star-a") + " "
        )
        right_stars = (
            " " + _cute_star_img("1.05em", "fcm-star-a")
            + _cute_star_img("0.7em", "fcm-star-b")
        )

    st.markdown(f"""
    <div class="fcm-header" style='text-align:center; padding:24px 20px;
                background:linear-gradient(135deg, {accent}, {grad_end});
                border-radius:14px; margin-bottom:20px;'>
        <h1 style='color:{title_color}; margin:0;
                   font-size:{text_size * 2}px;'>{left_stars}{app_title}{right_stars}</h1>
        <p style='color:{subtitle_color}; margin:12px 0 0 0;
                  font-size:{text_size}px;'>{app_subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def render_feedback_box(feedback_url, colour_scheme):
    """Footer feedback box tinted to match the active scheme."""
    palette = _get_scheme_palette(colour_scheme)
    text = palette["text"]
    accent = palette["accent"]
    border = _mix(palette["bg"], text, 0.18)

    st.markdown(f"""
    <div style='text-align:center; padding:20px; margin-top:40px;
                border-top:1px solid {border};'>
        <p style='color:{text};'>💬 Help improve this app!
        <a href='{feedback_url}' target='_blank'
           style='color:{accent}; font-weight:700;'>Take Survey</a></p>
    </div>
    """, unsafe_allow_html=True)


def render_mobile_settings_hint(colour_scheme="Soft Blue"):
    """Settings hint banner tinted to match the active scheme."""
    palette = _get_scheme_palette(colour_scheme)
    text = palette["text"]
    accent = palette["accent"]
    # Soft tinted background derived from the accent so it never clashes.
    box_bg = _mix(palette["bg"], accent, 0.12)
    border = _mix(palette["bg"], accent, 0.30)

    st.markdown(f"""
    <div style='background:{box_bg}; padding:10px 14px; border-radius:8px;
                margin-bottom:15px; text-align:center; font-size:14px;
                border:1px solid {border}; color:{text};'>
        ⚙️ Tap the <strong style='color:{accent};'>arrow icon</strong> in the top-left corner to open settings!
    </div>
    """, unsafe_allow_html=True)


def apply_styles(font_style, text_size, colour_scheme, line_spacing=1.8):
    """Re-theme the whole Streamlit app to the chosen scheme.

    Streamlit applies its boot-time theme (from config.toml) via CSS custom
    properties on :root and high-specificity data-testid rules. To beat that
    we (1) override those custom properties and (2) restate the key surfaces
    with matching selectors + !important. This runs on every rerun, so the
    dropdown re-paints the entire page, not just the cards.
    """
    palette = _get_scheme_palette(colour_scheme)
    bg = palette["bg"]
    text = palette["text"]
    accent = palette["accent"]
    card_bg = palette["card_bg"]

    dark = _is_dark(bg)
    # Panels (sidebar, inputs) sit slightly off the page bg so they read as
    # distinct surfaces. Lighten on dark schemes, use white on light schemes.
    panel_bg = _mix(bg, "#FFFFFF", 0.10) if dark else "#FFFFFF"
    input_bg = panel_bg
    # Subtle borders derived from the text colour so they're visible on any bg.
    border_col = _mix(bg, text, 0.22)
    muted_text = _mix(bg, text, 0.65)
    on_accent = _on_color(accent)
    placeholder_col = _mix(input_bg, text, 0.45)

    # Header banner colours (shared source of truth with render_header).
    _, _, header_title_col, header_subtitle_col = _header_colors(colour_scheme)
    star_col = _star_color(colour_scheme)

    st.markdown(f"""
    <style>
    /* ---- Hide anchor link icons Streamlit adds to headings ---- */
    h1 a, h2 a, h3 a {{ display: none !important; }}

    /* ---- Override Streamlit's theme variables at the root ---- */
    :root, .stApp {{
        --background-color: {bg} !important;
        --default-background-color: {bg} !important;
        --secondary-background-color: {panel_bg} !important;
        --text-color: {text} !important;
        --primary-color: {accent} !important;
        --font: '{font_style}', sans-serif !important;
    }}

    /* ---- Fonts + base text ---- */
    html, body, [class*="css"], .stApp, [data-testid="stMarkdownContainer"] {{
        font-family: '{font_style}', sans-serif !important;
    }}
    .stApp p, .stApp li, .stApp label, .stApp span, .stMarkdown {{
        font-size: {text_size}px !important;
        line-height: {line_spacing} !important;
        color: {text} !important;
    }}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
        color: {text} !important;
        font-family: '{font_style}', sans-serif !important;
    }}

    /* ---- Page background (multiple containers for reliability) ---- */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main, .block-container {{
        background-color: {bg} !important;
        color: {text} !important;
    }}
    [data-testid="stHeader"], header[data-testid="stHeader"] {{
        background: {bg} !important;
    }}

    /* ---- Sidebar ---- */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div {{
        background-color: {panel_bg} !important;
    }}
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {{
        color: {text} !important;
    }}

    /* ---- Captions / hints ---- */
    .stApp [data-testid="stCaptionContainer"],
    .stApp small {{
        color: {muted_text} !important;
    }}

    /* ---- Text inputs / textareas ---- */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {{
        background-color: {input_bg} !important;
        color: {text} !important;
        border: 1px solid {border_col} !important;
        border-radius: 8px !important;
    }}
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
        color: {placeholder_col} !important;
        opacity: 1 !important;
    }}

    /* ---- Selectboxes (BaseWeb) ---- */
    div[data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        color: {text} !important;
        border: 1px solid {border_col} !important;
        border-radius: 8px !important;
    }}
    div[data-baseweb="select"] svg {{ fill: {text} !important; }}
    /* dropdown menu popover */
    div[data-baseweb="popover"] li,
    ul[role="listbox"] li {{
        background-color: {input_bg} !important;
        color: {text} !important;
    }}
    div[data-baseweb="popover"] li:hover,
    ul[role="listbox"] li:hover {{
        background-color: {_mix(input_bg, accent, 0.20)} !important;
    }}

    /* ---- Radio + checkbox ---- */
    .stRadio label, .stCheckbox label,
    [data-testid="stWidgetLabel"] label,
    [data-testid="stWidgetLabel"] p {{
        color: {text} !important;
    }}

    /* ---- Buttons (cover old + new Streamlit testids) ---- */
    .stButton > button,
    .stDownloadButton > button,
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-primary"],
    [data-testid="baseButton-secondary"],
    [data-testid="baseButton-primary"] {{
        background-color: {accent} !important;
        color: {on_accent} !important;
        border: 1px solid {accent} !important;
        border-radius: 10px !important;
        padding: 10px 20px !important;
        font-weight: 700 !important;
    }}
    .stButton > button *, .stDownloadButton > button * {{
        color: {on_accent} !important;
    }}
    .stButton > button:hover,
    .stDownloadButton > button:hover {{
        filter: brightness(1.08) !important;
    }}
    .stButton > button:disabled,
    .stDownloadButton > button:disabled {{
        opacity: 0.4 !important;
    }}

    /* ---- File uploader ---- */
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploaderDropzone"] {{
        background-color: {input_bg} !important;
        border: 1px dashed {border_col} !important;
        color: {text} !important;
    }}
    [data-testid="stFileUploader"] section * {{ color: {text} !important; }}

    /* ---- Slider ---- */
    .stSlider [data-baseweb="slider"] div[role="slider"] {{
        background-color: {accent} !important;
    }}
    .stSlider [data-testid="stTickBar"] {{ color: {muted_text} !important; }}

    /* ---- Links ---- */
    .stApp a {{ color: {accent} !important; }}

    /* ---- Header banner (HIGHER specificity than the blanket h1/p rules) ---- */
    /* These win because `.stApp .fcm-header h1` (0,2,1) beats `.stApp h1`     */
    /* (0,1,1). Set here in a <style> block - not inline - because Streamlit   */
    /* strips !important from inline style attributes.                         */
    .stApp .fcm-header h1 {{
        color: {header_title_col} !important;
    }}
    .stApp .fcm-header p {{
        color: {header_subtitle_col} !important;
    }}
    .stApp .fcm-header h1 * {{
        color: {header_title_col} !important;
    }}
    /* Decorative stars: themed colour + a crisp 1px outline in the title    */
    /* colour so they pop on any banner. Higher specificity (0,3,0) than the  */
    /* `.fcm-header h1 *` rule (0,2,1) so the star colour wins.               */
    .stApp .fcm-header .fcm-star {{
        color: {star_col} !important;
        display: inline-block;
        text-shadow: -1px -1px 0 {header_title_col}, 1px -1px 0 {header_title_col},
                     -1px 1px 0 {header_title_col}, 1px 1px 0 {header_title_col};
    }}
    .stApp .fcm-header .fcm-star-sm {{
        font-size: 0.6em;
        vertical-align: 0.25em;
        opacity: 0.9;
    }}
    /* Cute star gentle bob + wiggle. Disabled automatically when the user   */
    /* has asked their device for reduced motion (sensory-friendly).         */
    @keyframes fcmStarBob {{
        0%, 100% {{ transform: translateY(0) rotate(0deg); }}
        30%      {{ transform: translateY(-3px) rotate(-7deg); }}
        60%      {{ transform: translateY(-1px) rotate(7deg); }}
    }}
    .stApp .fcm-header .fcm-star-svg {{
        animation: fcmStarBob 2.6s ease-in-out infinite;
        transform-origin: 50% 60%;
    }}
    .stApp .fcm-header .fcm-star-b {{
        animation-duration: 3.2s;
        animation-delay: 0.5s;
    }}
    @media (prefers-reduced-motion: reduce) {{
        .stApp .fcm-header .fcm-star-svg {{ animation: none; }}
    }}
    </style>
    """, unsafe_allow_html=True)
