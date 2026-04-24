# utils.py - helper functions for the flashcard app

import streamlit as st
import re
import os
import requests
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


# --- download helpers for "save as PNG" feature ---

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_image_bytes(url):
    """download raw bytes for a wikipedia image url. cached for the session
    so the same image isn't re-fetched when the user downloads cards.
    returns None on any error - the renderer will draw a no-image card."""
    if not url:
        return None
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "FlashcardApp/1.0 (educational use)"},
            timeout=10,
        )
        if r.ok:
            return r.content
    except Exception:
        pass
    return None


def build_cards_zip(flashcards, card_images, colors, page_bg_hex, cache_key):
    """build a ZIP of PNG flashcards. cache_key is a stable fingerprint of
    the inputs (deck contents + scheme) - we accept it as a parameter rather
    than computing it here so st.cache_data can hash it cheaply. callers
    must pass a cache_key that changes iff the zip contents should change."""
    return _build_cards_zip_cached(
        tuple((c["title"], tuple((f.get("text", "") if isinstance(f, dict) else str(f)) for f in c["facts"])) for c in flashcards),
        tuple(card_images.get(i) for i in range(len(flashcards))),
        page_bg_hex,
        colors["accent"],
        colors["text"],
        colors["label"],
        cache_key,
    )


@st.cache_data(show_spinner=False, ttl=3600)
def _build_cards_zip_cached(cards_fingerprint, image_urls, page_bg_hex, accent, text, label, cache_key):
    """inner cached function - hashes on primitives only so streamlit can
    cache it. reconstructs the flashcards from the fingerprint."""
    import io as _io
    import zipfile as _zipfile
    import re as _re

    colors = {"accent": accent, "text": text, "label": label}
    total = len(cards_fingerprint)
    zip_buf = _io.BytesIO()
    with _zipfile.ZipFile(zip_buf, "w", _zipfile.ZIP_DEFLATED) as zf:
        for i, (title, fact_texts) in enumerate(cards_fingerprint):
            c = {
                "title": title,
                "facts": [{"emoji": "*", "text": t} for t in fact_texts],
            }
            url = image_urls[i]
            image_bytes = fetch_image_bytes(url) if url else None
            png = render_card_to_png(
                card=c,
                colors=colors,
                idx=i,
                total=total,
                wiki_image_bytes=image_bytes,
                page_bg_hex=page_bg_hex,
            )
            safe_title = _re.sub(r"[^a-zA-Z0-9_-]+", "_", title).strip("_") or "card"
            zf.writestr(f"card_{i + 1}_{safe_title}.png", png)
    return zip_buf.getvalue()


def _hex_to_rgb(h):
    """#RRGGBB -> (R, G, B)."""
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _wrap_text_for_png(text, font, max_width, draw):
    """greedy word-wrap for the PNG renderer: build lines by adding words
    until the next word would exceed max_width."""
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
    """render ONE flashcard as a PNG and return the raw bytes.

    DESIGN NOTE: this deliberately doesn't try to match the browser version
    pixel-for-pixel. Pillow can't render colour emoji (🦒, 🪨 etc) and can't
    load web fonts like OpenDyslexic, so attempting an exact match produces
    broken boxes in place of missing glyphs. instead, we render a clean,
    print-friendly variant: em-dash separators instead of sparkles, numbered
    badge instead of topic emoji, bullet dots instead of per-fact emoji,
    DejaVu Sans (bundled with Pillow) instead of the user's chosen font.
    all of which means the PNG looks like a clean sibling of the on-screen
    card - same colours, same structure, same vibe - rather than a broken
    attempt at the same render.
    """
    W = 700
    MARGIN = 30
    ACCENT_BAR_W = 6
    PAD_X = 30
    PAD_Y = 30
    IMG_MAX_H = 260
    IMG_MAX_W = W - (MARGIN * 2) - (PAD_X * 2)
    FOOTER_H = 36

    accent      = _hex_to_rgb(colors["accent"])
    text_color  = _hex_to_rgb(colors["text"])
    label_color = _hex_to_rgb(colors["label"])
    card_bg     = (255, 254, 249)
    page_bg     = _hex_to_rgb(page_bg_hex)

    try:
        f_label  = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)
        f_title  = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        f_body   = ImageFont.truetype("DejaVuSans.ttf", 18)
        f_footer = ImageFont.truetype("DejaVuSans.ttf", 12)
        f_badge  = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except (OSError, IOError):
        f_label = f_title = f_body = f_footer = f_badge = ImageFont.load_default()

    # --- pre-pass: compute canvas height before drawing ---
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
        except Exception:
            pil_image = None
            image_height_used = 0

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

    content_h = (
        PAD_Y + 24 + 14
        + image_height_used
        + title_block_h + 18
        + facts_block_h
        + PAD_Y
    )
    H = content_h + FOOTER_H + (MARGIN * 2)

    # --- draw for real ---
    img = Image.new("RGB", (W, H), page_bg)
    draw = ImageDraw.Draw(img)

    card_x0, card_y0 = MARGIN, MARGIN
    card_x1, card_y1 = W - MARGIN, H - MARGIN - FOOTER_H

    draw.rounded_rectangle([card_x0, card_y0, card_x1, card_y1], radius=16, fill=card_bg)
    draw.rounded_rectangle(
        [card_x0, card_y0, card_x0 + ACCENT_BAR_W, card_y1],
        radius=3, fill=accent,
    )

    y = card_y0 + PAD_Y
    label_text = f"- CARD {idx + 1} OF {total} -"
    lb_bbox = draw.textbbox((0, 0), label_text, font=f_label)
    lb_w = lb_bbox[2] - lb_bbox[0]
    draw.text(((W - lb_w) // 2, y), label_text, font=f_label, fill=label_color)
    y += 24 + 14

    if pil_image is not None:
        img_w, img_h = pil_image.size
        img_x = (W - img_w) // 2
        draw.rounded_rectangle(
            [img_x - 4, y - 4, img_x + img_w + 4, y + img_h + 4],
            radius=14, fill=accent,
        )
        mask = Image.new("L", (img_w, img_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, img_w, img_h], radius=10, fill=255)
        img.paste(pil_image, (img_x, y), mask)

        sticker_r = 26
        sticker_cx = img_x + img_w - 6
        sticker_cy = y - 6
        draw.ellipse(
            [sticker_cx - sticker_r, sticker_cy - sticker_r,
             sticker_cx + sticker_r, sticker_cy + sticker_r],
            fill=accent, outline=card_bg, width=3,
        )
        badge_text = str(idx + 1)
        bt_bbox = draw.textbbox((0, 0), badge_text, font=f_badge)
        bt_w = bt_bbox[2] - bt_bbox[0]
        bt_h = bt_bbox[3] - bt_bbox[1]
        draw.text(
            (sticker_cx - bt_w // 2, sticker_cy - bt_h // 2 - 2),
            badge_text, font=f_badge, fill=card_bg,
        )
        y += img_h + 20

    for line in title_lines:
        t_bbox = draw.textbbox((0, 0), line, font=f_title)
        draw.text(((W - (t_bbox[2] - t_bbox[0])) // 2, y), line, font=f_title, fill=text_color)
        y += 36
    y += 10

    draw.line(
        [(card_x0 + PAD_X, y), (card_x1 - PAD_X, y)],
        fill=accent, width=1,
    )
    y += 18

    fact_x = card_x0 + PAD_X
    text_x = fact_x + BULLET_W + 8
    for lines in wrapped_facts:
        draw.text((fact_x, y), "*", font=f_body, fill=accent)
        for line in lines:
            draw.text((text_x, y), line, font=f_body, fill=text_color)
            y += 26
        y += 10

    footer_text = "Made with Simple Facts with Simple Images"
    ft_bbox = draw.textbbox((0, 0), footer_text, font=f_footer)
    ft_w = ft_bbox[2] - ft_bbox[0]
    draw.text(
        ((W - ft_w) // 2, H - MARGIN - 14),
        footer_text, font=f_footer, fill=label_color,
    )

    out = BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


# --- Wikipedia image search ---

@st.cache_data(show_spinner=False)
def search_wikipedia_image(query):
    """search wikipedia for a picture that matches the topic"""
    try:
        clean_query = re.sub(r'[^\w\s-]', '', query).strip()
        if not clean_query:
            return None
        
        search_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": clean_query,
            "gsrlimit": 5,
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
        
        junk_keywords = ['disambiguation', 'list of', '(surname)', '(given name)']
        
        query_words = set(clean_query.lower().split())
        best_match = None
        best_score = 0
        
        for page_id, page_data in pages.items():
            if "thumbnail" not in page_data:
                continue
            
            page_title = page_data.get("title", "").lower()
            
            if any(junk in page_title for junk in junk_keywords):
                continue
            
            title_words = set(page_title.split())
            overlap = len(query_words & title_words)
            
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
    nothing read them - trimmed to keep the schema honest."""
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
            "text":   "#1B5E20",
            "label":  "#2F7A55",
            "accent": "#4CAF50",
        },
        "Low Stimulation": {
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


@st.cache_data(show_spinner=False, ttl=3600)
def generate_flashcards_from_llm(raw_text, reading_level="intermediate"):
    """send text to claude and get flashcards back"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("Can't find the AI key - please check your settings.")
        return None
    
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
- Write numbers as digits (5, 100) not words (five, one hundred) - easier for dyslexic readers to process.
- Avoid double negatives. "It is helpful" beats "It is not unhelpful."
- At the Easy reading level ONLY: no idioms, metaphors, or figurative language. Some learners take these literally.

EMOJI RULES (per fact):
- Each fact gets ONE emoji that represents THAT fact's content, not the card topic as a whole.
- Pick concrete and memorable emojis. A whale-sound fact gets 🔊, a whale-size fact gets 📏, a whale-food fact gets 🦐.
- Use different emojis for different facts on the same card.

IMAGE SEARCH RULES (CRITICAL - getting this wrong gives learners the wrong picture):
- image_search must name the MAIN SUBJECT of the card, NOT its habitat, context, action, or property.
  - Card titled "Where Giraffes Live" -> use "giraffe" (NOT "African savanna" - that page's photo is often an elephant).
  - Card titled "How DNA Copies Itself" -> use "DNA" (NOT "cell division" or "genetic replication").
  - Card titled "What Elephants Eat" -> use "elephant" (NOT "plants" or "African vegetation").
  - Card titled "The Life Cycle of Butterflies" -> use "butterfly" (NOT "life cycle" or "metamorphosis").
- The subject must be PHOTOGRAPHABLE - Wikipedia needs an actual photo of it.
- For genuinely abstract concepts (no physical subject), pick a concrete stand-in: "inflation" -> "shopping basket", "democracy" -> "ballot box", "friendship" -> "people holding hands".
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
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}],
                "tools": [FLASHCARD_TOOL],
                "tool_choice": {"type": "tool", "name": "create_flashcards"},
            },
            timeout=30
        )
        
        if response.status_code != 200:
            st.error("Something went wrong talking to the AI - please try again in a moment.")
            return None
        
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
        @media (prefers-reduced-motion) rule further down in the CSS -
        this is an in-app override some users prefer.
    """
    
    colors = {
        "Soft Blue":                  {"bg": "#E8F1F5", "text": "#1C3A42", "accent": "#3A7CA5"},
        "Pale Lavender":              {"bg": "#F5E8F5", "text": "#3C2C42", "accent": "#7C3C9C"},
        "Pale Mint":                  {"bg": "#E8F5F1", "text": "#1C3C32", "accent": "#2F7A55"},
        "Low Stimulation":            {"bg": "#F2F2EC", "text": "#2E2E2E", "accent": "#555555"},
    }
    
    c = colors.get(colour_scheme, colors["Low Stimulation"])
    
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
       Both @import lines degrade gracefully - if the CDN is unreachable,
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
        background-color:
        color: var(--text) !important;
    }}
    
    [data-testid="stTextArea"] textarea {{
        background-color:
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
        background-color:
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
       on selectboxes we DON'T outline the whole component (too big - wraps
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
        color:
        border-radius: 6px !important;
        margin: 2px 4px !important;
    }}

    /* pointer cursor on every interactive setting in the sidebar.
       browsers default to the text I-beam on form inputs, but for
       click-to-pick controls (selectbox, slider, checkbox) the pointer
       hand is the clearer signal - matches the "Make Flashcard" button
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
       to migraines often have this enabled - it's enforced from Windows,
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
