# utils.py - Complete helper functions for the flashcard app

import streamlit as st
import re
import os
import requests
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from config import get_emoji_for_text, COLOR_SCHEMES

# --- LocalStorage helpers for saving decks ---

@st.dialog("💾 Save Current Deck")
def save_deck_dialog():
    """Dialog for saving current flashcards to localStorage"""
    st.markdown("### Name your deck")
    deck_name = st.text_input("Deck name", placeholder="e.g., Biology Chapter 3")
    
    if st.button("Save Deck", type="primary"):
        if deck_name and st.session_state.flashcards:
            # Get existing decks from localStorage
            existing_decks = st.session_state.get("saved_decks", {})
            
            # Save current deck
            existing_decks[deck_name] = {
                "flashcards": st.session_state.flashcards,
                "card_images": st.session_state.card_images,
                "created": str(__import__("datetime").datetime.now()),
                "card_count": len(st.session_state.flashcards)
            }
            
            # Store back to session state (will be saved to localStorage via JS)
            st.session_state.saved_decks = existing_decks
            
            # JavaScript to save to localStorage
            st.markdown(f"""
            <script>
            localStorage.setItem('flashcard_decks', JSON.stringify({json.dumps(existing_decks)}));
            </script>
            """, unsafe_allow_html=True)
            
            st.success(f"✅ Deck '{deck_name}' saved!")
            st.rerun()
        elif not deck_name:
            st.warning("Please enter a deck name")

def load_decks_from_storage():
    """Load saved decks from localStorage on app start"""
    st.markdown("""
    <script>
    const decks = localStorage.getItem('flashcard_decks');
    if (decks) {
        window.parent.postMessage({type: 'streamlit:setComponentValue', value: decks}, '*');
    }
    </script>
    """, unsafe_allow_html=True)

# --- Wikipedia image search with better filtering ---

@st.cache_data(show_spinner=False, ttl=3600)
def search_wikipedia_image(query):
    """Search Wikipedia for a relevant image - improved filtering"""
    try:
        clean_query = re.sub(r'[^\w\s-]', '', query).strip()
        if not clean_query:
            return None
        
        # First try: Exact page match
        page_url = f"https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "titles": clean_query,
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": 500,
        }
        
        response = requests.get(page_url, params=params, timeout=5,
                                headers={"User-Agent": "FlashcardApp/1.0"})
        
        if response.status_code == 200:
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if "thumbnail" in page_data and int(page_id) > 0:
                    # Verify it's not a disambiguation page
                    title = page_data.get("title", "").lower()
                    bad_words = ['disambiguation', 'list of', '(disambiguation)', 'may refer to']
                    if not any(bad in title for bad in bad_words):
                        return page_data["thumbnail"]["source"]
        
        # Second try: Search for best match
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": clean_query,
            "gsrlimit": 10,
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": 500,
        }
        
        response = requests.get(page_url, params=params, timeout=5,
                                headers={"User-Agent": "FlashcardApp/1.0"})
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        
        # Filter out bad pages
        junk_keywords = ['disambiguation', 'list of', '(surname)', '(given name)', 
                        'may refer to', 'disambiguation page', 'index of']
        
        query_words = set(clean_query.lower().split())
        best_match = None
        best_score = 0
        
        for page_id, page_data in pages.items():
            if "thumbnail" not in page_data or int(page_id) < 0:
                continue
            
            page_title = page_data.get("title", "").lower()
            
            # Skip junk pages
            if any(junk in page_title for junk in junk_keywords):
                continue
            
            # Score by word overlap
            title_words = set(page_title.split())
            overlap = len(query_words & title_words)
            
            # Bonus for exact match
            if clean_query.lower() == page_title:
                overlap += 5
            
            if overlap > best_score:
                best_score = overlap
                best_match = page_data["thumbnail"]["source"]
        
        return best_match
    except Exception:
        return None

# --- Image search with Unsplash fallback ---

@st.cache_data(show_spinner=False, ttl=3600)
def search_unsplash_image(query):
    """Search Unsplash for high-quality images (better than Wikipedia)"""
    try:
        # Unsplash requires an access key - free tier available
        # For now, fall back to Wikipedia. To enable Unsplash:
        # 1. Sign up at unsplash.com/developers
        # 2. Get access key and add to secrets
        # 3. Uncomment below
        unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
        if not unsplash_key:
            return None
        
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": query,
            "per_page": 1,
            "orientation": "landscape"
        }
        headers = {"Authorization": f"Client-ID {unsplash_key}"}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                return data["results"][0]["urls"]["regular"]
    except Exception:
        pass
    return None

def get_best_image(query):
    """Try Unsplash first, then Wikipedia as fallback"""
    # Try Unsplash first (better quality)
    img = search_unsplash_image(query)
    if img:
        return img
    # Fall back to Wikipedia
    return search_wikipedia_image(query)

# --- Card colors with support for multiple schemes ---

def get_card_colors(colour_scheme, mode="Accessibility"):
    """Get colors for the current scheme and mode"""
    schemes = COLOR_SCHEMES.get(mode, COLOR_SCHEMES["Accessibility"])
    colors = schemes.get(colour_scheme, schemes["Soft Blue"])
    
    return {
        "text": colors["text"],
        "label": colors["accent"],
        "accent": colors["accent"],
        "card_bg": colors["card_bg"],
        "bg": colors["bg"]
    }

# --- Enhanced emoji matching ---

def get_topic_emoji(title, facts=None):
    """Get emoji for card topic with context from facts"""
    # Combine title and first few facts for better matching
    context = title
    if facts and len(facts) > 0:
        facts_text = " ".join([f.get('text', '')[:50] for f in facts[:2]])
        context = f"{title} {facts_text}"
    
    return get_emoji_for_text(context)

# --- DeepSeek flashcard generation ---

FLASHCARD_SYSTEM_PROMPT = """You are a helpful tutor creating accessible flashcards. 
Return ONLY valid JSON in this format:
{
  "flashcards": [
    {
      "title": "short topic (2-4 words)",
      "topic_keyword": "main keyword for emoji",
      "image_search": "concrete noun for image search",
      "facts": [
        {"text": "fact about the topic", "emoji_hint": "suggested emoji keyword"},
        {"text": "another fact", "emoji_hint": "another emoji keyword"}
      ]
    }
  ]
}

Rules:
- Each card: 2-3 facts, each 8-20 words
- Use active voice, short sentences
- Numbers as digits (5 not "five")
- image_search = main subject (e.g., "giraffe" not "African savanna")
- emoji_hint = concrete noun for emoji (e.g., "heart", "star", "book")
"""

@st.cache_data(show_spinner=False, ttl=3600)
def generate_flashcards_from_llm(raw_text, reading_level="intermediate"):
    """Generate flashcards using DeepSeek API"""
    
    from openai import OpenAI
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["DEEPSEEK_API_KEY"]
        except:
            st.error("🔑 Missing DeepSeek API key")
            st.info("Get a free key at https://platform.deepseek.com/")
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
    level_instructions = {
        "simple": "Easy (ages 4-11): Very simple words, 8-12 words per fact, friendly tone",
        "intermediate": "Medium (ages 11-18): Clear language, 12-18 words per fact, explain terms",
        "complex": "Advanced (18+): Precise academic language, up to 25 words per fact"
    }.get(reading_level, "Medium level")
    
    prompt = f"""Create {min_cards}-{max_cards} flashcards from this text.

Reading level: {level_instructions}

Text: {raw_text[:18000]}

Return JSON matching the required format exactly."""
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": FLASHCARD_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        flashcard_data = result.get("flashcards", [])
        
        if not flashcard_data:
            st.error("No flashcards generated")
            return None
        
        # Convert to app format with emojis
        flashcards = []
        for card in flashcard_data:
            # Get topic emoji
            topic_emoji = get_topic_emoji(card.get("title", ""), card.get("facts", []))
            
            # Process facts with emojis
            normalized_facts = []
            for fact in card.get('facts', []):
                if isinstance(fact, dict):
                    fact_text = fact.get('text', '')
                    emoji_hint = fact.get('emoji_hint', '')
                    
                    # Get emoji for this fact
                    if emoji_hint:
                        fact_emoji = get_emoji_for_text(emoji_hint)
                    else:
                        fact_emoji = get_emoji_for_text(fact_text[:30])
                    
                    normalized_facts.append({
                        'emoji': fact_emoji,
                        'text': fact_text.strip(),
                    })
                elif isinstance(fact, str):
                    normalized_facts.append({
                        'emoji': topic_emoji,
                        'text': fact.strip(),
                    })
            
            flashcards.append({
                'title': card.get('title', 'Topic'),
                'facts': normalized_facts,
                'emoji': topic_emoji,
                'image_search': card.get('image_search', card.get('title', 'topic')),
            })
        
        return flashcards
    
    except Exception as e:
        st.error(f"Failed to generate flashcards: {str(e)}")
        return None

# --- File extraction ---

def extract_text_from_file(uploaded_file):
    """Extract text from PDF, DOCX, or TXT"""
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
            return "Unsupported file type"
    except Exception:
        return "Error reading file"

# --- PNG rendering ---

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _wrap_text_for_png(text, font, max_width, draw):
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for w in words[1:]:
        trial = f"{current} {w}"
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = w
    lines.append(current)
    return lines

def render_card_to_png(card, colors, idx, total, wiki_image_bytes=None, page_bg_hex="#F5F1E8"):
    """Render flashcard as PNG"""
    W = 700
    MARGIN = 30
    ACCENT_BAR_W = 6
    PAD_X = 30
    PAD_Y = 30
    IMG_MAX_H = 260
    IMG_MAX_W = W - (MARGIN * 2) - (PAD_X * 2)
    FOOTER_H = 36

    accent = _hex_to_rgb(colors["accent"])
    text_color = _hex_to_rgb(colors["text"])
    label_color = _hex_to_rgb(colors["label"])
    card_bg = _hex_to_rgb(colors.get("card_bg", "#FFFEF9"))
    page_bg = _hex_to_rgb(page_bg_hex)

    try:
        f_label = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)
        f_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        f_body = ImageFont.truetype("DejaVuSans.ttf", 18)
        f_footer = ImageFont.truetype("DejaVuSans.ttf", 12)
        f_badge = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except:
        f_label = f_title = f_body = f_footer = f_badge = ImageFont.load_default()

    # Calculate height
    tmp = Image.new("RGB", (10, 10))
    d_tmp = ImageDraw.Draw(tmp)

    image_height_used = 0
    pil_image = None
    if wiki_image_bytes:
        try:
            pil_image = Image.open(BytesIO(wiki_image_bytes)).convert("RGB")
            iw, ih = pil_image.size
            scale = min(IMG_MAX_W / iw, IMG_MAX_H / ih)
            new_w = int(iw * scale)
            new_h = int(ih * scale)
            pil_image = pil_image.resize((new_w, new_h), Image.LANCZOS)
            image_height_used = new_h + 20
        except:
            pass

    title_lines = _wrap_text_for_png(card["title"], f_title, IMG_MAX_W, d_tmp)
    title_block_h = len(title_lines) * 36 + 10

    BULLET_W = 24
    FACT_INDENT = BULLET_W + 8
    facts_block_h = 0
    wrapped_facts = []
    for fact in card["facts"]:
        text = fact.get("text", "") if isinstance(fact, dict) else str(fact)
        lines = _wrap_text_for_png(text, f_body, IMG_MAX_W - FACT_INDENT, d_tmp)
        wrapped_facts.append(lines)
        facts_block_h += len(lines) * 26 + 10

    content_h = PAD_Y + 24 + 14 + image_height_used + title_block_h + 18 + facts_block_h + PAD_Y
    H = content_h + FOOTER_H + (MARGIN * 2)

    # Draw
    img = Image.new("RGB", (W, H), page_bg)
    draw = ImageDraw.Draw(img)

    card_x0, card_y0 = MARGIN, MARGIN
    card_x1, card_y1 = W - MARGIN, H - MARGIN - FOOTER_H

    draw.rounded_rectangle([card_x0, card_y0, card_x1, card_y1], radius=16, fill=card_bg)
    draw.rounded_rectangle([card_x0, card_y0, card_x0 + ACCENT_BAR_W, card_y1], radius=3, fill=accent)

    y = card_y0 + PAD_Y
    label_text = f"- CARD {idx + 1} OF {total} -"
    lb_bbox = draw.textbbox((0, 0), label_text, font=f_label)
    lb_w = lb_bbox[2] - lb_bbox[0]
    draw.text(((W - lb_w) // 2, y), label_text, font=f_label, fill=label_color)
    y += 24 + 14

    if pil_image:
        img_w, img_h = pil_image.size
        img_x = (W - img_w) // 2
        draw.rounded_rectangle([img_x - 4, y - 4, img_x + img_w + 4, y + img_h + 4], radius=14, fill=accent)
        mask = Image.new("L", (img_w, img_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, img_w, img_h], radius=10, fill=255)
        img.paste(pil_image, (img_x, y), mask)

        sticker_r = 26
        sticker_cx = img_x + img_w - 6
        sticker_cy = y - 6
        draw.ellipse([sticker_cx - sticker_r, sticker_cy - sticker_r, sticker_cx + sticker_r, sticker_cy + sticker_r], fill=accent, outline=card_bg, width=3)
        badge_text = str(idx + 1)
        bt_bbox = draw.textbbox((0, 0), badge_text, font=f_badge)
        bt_w = bt_bbox[2] - bt_bbox[0]
        bt_h = bt_bbox[3] - bt_bbox[1]
        draw.text((sticker_cx - bt_w // 2, sticker_cy - bt_h // 2 - 2), badge_text, font=f_badge, fill=card_bg)
        y += img_h + 20

    for line in title_lines:
        t_bbox = draw.textbbox((0, 0), line, font=f_title)
        draw.text(((W - (t_bbox[2] - t_bbox[0])) // 2, y), line, font=f_title, fill=text_color)
        y += 36
    y += 10

    draw.line([(card_x0 + PAD_X, y), (card_x1 - PAD_X, y)], fill=accent, width=1)
    y += 18

    fact_x = card_x0 + PAD_X
    text_x = fact_x + BULLET_W + 8
    for lines in wrapped_facts:
        draw.text((fact_x, y), "*", font=f_body, fill=accent)
        for line in lines:
            draw.text((text_x, y), line, font=f_body, fill=text_color)
            y += 26
        y += 10

    footer_text = "Made with Flashcard Magic"
    ft_bbox = draw.textbbox((0, 0), footer_text, font=f_footer)
    ft_w = ft_bbox[2] - ft_bbox[0]
    draw.text(((W - ft_w) // 2, H - MARGIN - 14), footer_text, font=f_footer, fill=label_color)

    out = BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()

def fetch_image_bytes(url):
    """Download image bytes for PNG export"""
    if not url:
        return None
    try:
        r = requests.get(url, headers={"User-Agent": "FlashcardApp/1.0"}, timeout=10)
        if r.ok:
            return r.content
    except:
        pass
    return None

# --- Fun header with animations ---

def render_header(app_title, app_subtitle, text_size, colour_scheme, fun_mode=True):
    """Render animated header with fun mode option"""
    
    if fun_mode:
        st.markdown("""
        <style>
        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            50% { transform: translateY(-10px) rotate(5deg); }
        }
        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        .fun-title {
            background: linear-gradient(135deg, #FF6B6B, #4ECDC4, #45B7D1, #96CEB4);
            background-size: 300% 300%;
            animation: gradient 6s ease infinite;
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent !important;
            display: inline-block;
        }
        .floating-emoji {
            display: inline-block;
            animation: float 2s ease-in-out infinite;
        }
        </style>
        """, unsafe_allow_html=True)
        
        title_px = text_size * 2
        st.markdown(f"""
        <div style='text-align: center; padding: 30px 20px;'>
            <div class='floating-emoji' style='font-size: 50px; margin-bottom: 10px;'>✨</div>
            <div class='fun-title' style='font-size: {title_px}px; font-weight: 900;'>{app_title}</div>
            <div style='font-size: {text_size}px; color: #666; margin-top: 10px;'>{app_subtitle}</div>
            <div class='floating-emoji' style='font-size: 40px; margin-top: 10px;'>📚</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Simple header for accessibility mode
        title_px = text_size * 1.8
        st.markdown(f"""
        <div style='padding: 20px; border-bottom: 3px solid #ccc;'>
            <div style='font-size: {title_px}px; font-weight: bold;'>{app_title}</div>
            <div style='font-size: {text_size}px; color: #555;'>{app_subtitle}</div>
        </div>
        """, unsafe_allow_html=True)

# --- Apply styles with fun mode support ---

def apply_styles(font_style, text_size, colour_scheme, mode="Accessibility", fun_mode=True, line_spacing=1.8):
    """Apply CSS styles to the app"""
    
    schemes = COLOR_SCHEMES.get(mode, COLOR_SCHEMES["Accessibility"])
    colors = schemes.get(colour_scheme, list(schemes.values())[0])
    
    bg_color = colors["bg"]
    text_color = colors["text"]
    accent_color = colors["accent"]
    
    extra_styles = ""
    if fun_mode:
        extra_styles = """
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(0,0,0,0.15) !important;
            transition: all 0.2s ease !important;
        }
        """
    
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family={font_style.replace(" ", "+")}&display=swap');
    
    :root {{
        --bg: {bg_color};
        --text: {text_color};
        --accent: {accent_color};
        --font: '{font_style}', sans-serif;
        --size: {text_size}px;
        --line-height: {line_spacing};
    }}
    
    [data-testid="stAppViewContainer"] {{ background-color: var(--bg) !important; }}
    [data-testid="stMainBlockContainer"] {{ background-color: var(--bg) !important; }}
    
    p, span, li, label, div {{
        font-family: var(--font) !important;
        font-size: var(--size) !important;
        color: var(--text) !important;
        line-height: var(--line-height) !important;
    }}
    
    h1, h2, h3, h4, h5, h6 {{
        font-family: var(--font) !important;
        color: var(--accent) !important;
    }}
    
    button {{
        font-family: var(--font) !important;
        border-radius: 12px !important;
        transition: all 0.2s ease !important;
    }}
    
    {extra_styles}
    </style>
    """, unsafe_allow_html=True)
