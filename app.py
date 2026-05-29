# app.py - UPDATED MAIN FLASHCARD APP (Works with DeepSeek + Fixed Images)
# Copy this entire code into app.py

import os
import re
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# Get DeepSeek API key (not Claude)
try:
    if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
        # Keep for backward compatibility, but we'll use DEEPSEEK_API_KEY
        pass
    if hasattr(st, "secrets") and "DEEPSEEK_API_KEY" in st.secrets:
        os.environ["DEEPSEEK_API_KEY"] = st.secrets["DEEPSEEK_API_KEY"]
except Exception:
    pass

# Create a neutral boot theme. The real per-scheme colours are applied at
# runtime by apply_styles() on every rerun, so this only needs to be a sane
# default for the very first paint before any scheme is chosen.
config_dir = os.path.expanduser("~/.streamlit")
config_file = os.path.join(config_dir, "config.toml")
if not os.path.exists(config_file):
    os.makedirs(config_dir, exist_ok=True)
    with open(config_file, "w") as f:
        f.write("""[theme]
primaryColor = "#3A7CA5"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F5F5F5"
textColor = "#1C1C1C"
font = "sans serif"
base = "light"

[client]
showErrorDetails = false
toolbarMode = "minimal"

[logger]
level = "error"
""")

from config import (
    APP_TITLE, APP_SUBTITLE, READING_LEVELS, FONT_OPTIONS,
    MIN_FONT_SIZE, MAX_FONT_SIZE, DEFAULT_FONT_SIZE, COLOR_SCHEMES
)
from utils import (
    apply_styles, extract_text_from_file,
    generate_flashcards_from_llm, get_card_colors,
    search_wikipedia_image, render_header,
    render_card_to_png, fetch_image_bytes, build_cards_zip,
    render_mobile_settings_hint, twemojify,
)

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
defaults = {
    "flashcard_generated": False,
    "flashcards": None,
    "font_style": "Verdana",
    "text_size": DEFAULT_FONT_SIZE,
    "colour_scheme": "Soft Blue",
    "card_flipped": {},
    "card_images": {},
    "current_card_idx": 0,
    "line_spacing": 1.8,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

apply_styles(
    st.session_state.font_style,
    st.session_state.text_size,
    st.session_state.colour_scheme,
    st.session_state.line_spacing,
)

DECORATION_EMOJIS = ['✨', '⭐', '💫', '🌟', '🎯', '📚', '💡', '🎨']
MAX_CHARS = 70000

# Derive scheme metadata from the central COLOR_SCHEMES table.
# ALL_SCHEME_NAMES: flat list in the order they appear in config (preserves grouping).
# SCHEME_GROUP: scheme name -> group label (e.g. "Soft Blue" -> "Accessibility").
# PAGE_BG_MAP: scheme name -> page background hex (used by PNG export).
ALL_SCHEME_NAMES = []
SCHEME_GROUP = {}
PAGE_BG_MAP = {}
for _group_name, _group in COLOR_SCHEMES.items():
    for _scheme_name, _palette in _group.items():
        ALL_SCHEME_NAMES.append(_scheme_name)
        SCHEME_GROUP[_scheme_name] = _group_name
        PAGE_BG_MAP[_scheme_name] = _palette["bg"]

# Friendlier group labels for the dropdown
_GROUP_LABEL = {
    "Accessibility": "Calm",
    "Vibrant": "Vibrant",
    "High Contrast": "High Contrast",
}

def _format_scheme(name):
    group = SCHEME_GROUP.get(name, "")
    label = _GROUP_LABEL.get(group, group)
    return f"{label} — {name}" if label else name

# --- header ---
render_header(APP_TITLE, APP_SUBTITLE, st.session_state.text_size, st.session_state.colour_scheme)

st.markdown("<div style='margin-bottom: 28px;'></div>", unsafe_allow_html=True)

# Mobile settings hint
render_mobile_settings_hint(st.session_state.colour_scheme)

# --- settings panel in sidebar ---
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    reading_level = st.selectbox("Reading Level", list(READING_LEVELS.keys()), key="reading_level_select")
    
    new_font = st.selectbox("Font Style", FONT_OPTIONS, index=FONT_OPTIONS.index(st.session_state.font_style), key="font_selectbox")
    if new_font != st.session_state.font_style:
        st.session_state.font_style = new_font
        st.rerun()
    
    new_size = st.slider("Text Size", MIN_FONT_SIZE, MAX_FONT_SIZE, st.session_state.text_size, key="text_size_slider")
    if new_size != st.session_state.text_size:
        st.session_state.text_size = new_size
        st.rerun()

    SPACING_OPTIONS = {"Tight (1.5)": 1.5, "Normal (1.8)": 1.8, "Loose (2.0)": 2.0}
    spacing_keys = list(SPACING_OPTIONS.keys())
    current_spacing_key = next(
        (k for k, v in SPACING_OPTIONS.items() if v == st.session_state.line_spacing),
        "Normal (1.8)",
    )
    new_spacing_key = st.selectbox(
        "Line Spacing",
        spacing_keys,
        index=spacing_keys.index(current_spacing_key),
        key="line_spacing_select",
        help="Space between lines of text. More space can help dyslexic readers; less space fits more on screen.",
    )
    if SPACING_OPTIONS[new_spacing_key] != st.session_state.line_spacing:
        st.session_state.line_spacing = SPACING_OPTIONS[new_spacing_key]
        st.rerun()

    colour_options = ALL_SCHEME_NAMES
    if st.session_state.colour_scheme not in colour_options:
        st.session_state.colour_scheme = "Soft Blue"
    new_colour = st.selectbox(
        "Colour Scheme",
        colour_options,
        index=colour_options.index(st.session_state.colour_scheme),
        format_func=_format_scheme,
        key="colour_selectbox",
        help="Calm = low-stimulation palettes for sensory comfort. Vibrant = brighter, more saturated. High Contrast = WCAG AAA pairings for low-vision and dyslexic readers.",
    )
    if new_colour != st.session_state.colour_scheme:
        st.session_state.colour_scheme = new_colour
        st.rerun()
    
    show_images = st.checkbox("Show Images", value=True, key="show_images_check", help="Show a picture on each card")
    
    st.markdown("---")
    st.caption("💡 These settings adjust the whole app. Change them any time - your cards won't disappear.")
    st.caption("🐕 Using DeepSeek API for flashcards")

# --- main content area ---
st.markdown("### 📝 Your Text")

input_type = st.radio("Input Type", ["Paste Text", "Upload File"], horizontal=True, label_visibility="collapsed")

if input_type == "Paste Text":
    user_text = st.text_area("Type or paste your text...", height=150, placeholder="Paste your text here...", label_visibility="collapsed")
else:
    uploaded_file = st.file_uploader("Upload a text file (TXT, PDF, or DOCX)", type=["txt", "pdf", "docx"], label_visibility="collapsed")
    if uploaded_file:
        user_text = extract_text_from_file(uploaded_file)
        st.success(f"✅ Loaded {uploaded_file.name}")
    else:
        user_text = ""

if user_text and len(user_text) > MAX_CHARS:
    st.info(f"ℹ️ Your text is quite long - we'll use the first {MAX_CHARS:,} characters to make flashcards.")
    user_text = user_text[:MAX_CHARS]

word_count = len(user_text.split()) if user_text else 0
st.caption(f"📝 {word_count} words")

st.caption("⚠️ Your text is sent to DeepSeek AI and Wikipedia to make the flashcards. Please don't paste anything confidential.")

_, btn, _ = st.columns([1, 1.2, 1])
with btn:
    if st.button("✨ Make Flashcards", use_container_width=True, key="make_flashcard_btn"):
        if not user_text.strip():
            st.warning("⚠️ Please enter or upload some text first!")
        elif word_count < 20:
            st.warning("⚠️ Please add a bit more text (at least 20 words) so the AI has enough to work with.")
        else:
            level_code = READING_LEVELS[reading_level]
            st.session_state.card_images = {}
            st.session_state.card_flipped = {}
            st.session_state.current_card_idx = 0
            
            with st.spinner("✨ Creating your flashcards..."):
                new_cards = generate_flashcards_from_llm(user_text, reading_level=level_code)
                if new_cards:
                    st.session_state.flashcards = new_cards
                    st.session_state.flashcard_generated = True

                # Generate images as part of the same step - no separate
                # status messages, so the user just sees finished cards.
                if new_cards and show_images:
                    from concurrent.futures import ThreadPoolExecutor
                    search_terms = [
                        (i, c.get('image_search', c['title']))
                        for i, c in enumerate(new_cards)
                    ]
                    with ThreadPoolExecutor(max_workers=5) as pool:
                        results = list(pool.map(
                            lambda item: (item[0], search_wikipedia_image(item[1])),
                            search_terms
                        ))
                    for idx, url in results:
                        st.session_state.card_images[idx] = url

if not st.session_state.flashcard_generated:
    st.markdown(
        "<p style='text-align:center; opacity:0.75; margin-top:20px;'>👆 Paste some text above to get started!</p>",
        unsafe_allow_html=True
    )

# --- show the flashcards ---
if st.session_state.flashcard_generated and st.session_state.flashcards:
    flashcards = st.session_state.flashcards
    
    for i in range(len(flashcards)):
        if i not in st.session_state.card_flipped:
            st.session_state.card_flipped[i] = False
    
    card_colors = get_card_colors(st.session_state.colour_scheme)
    
    st.markdown("---")
    st.markdown(f"### 📚 Your Flashcards ({len(flashcards)} cards)")
    
    flipped_count = sum(1 for i in range(len(flashcards)) if st.session_state.card_flipped.get(i, False))
    st.markdown(
        f"<div style='padding:10px; text-align:center; background:rgba(212, 160, 23, 0.1); border-radius:8px; font-weight:700; color:#D4A017; font-size:0.9em; margin:10px 0 20px 0;'>👀 Studied: {flipped_count}/{len(flashcards)}</div>",
        unsafe_allow_html=True
    )
    
    if flipped_count == len(flashcards):
        st.success("🎉 You've studied all the cards! Well done!")
    
    # Card styling functions
    def card_outer_style(accent_hex, card_bg, scheme=None):
        if scheme == "Low Stimulation":
            return (
                f"background:{card_bg};"
                f"border-radius:20px;"
                f"margin:12px auto;"
                f"max-width:860px;"
                f"border:2px solid {accent_hex};"
                f"overflow:hidden;"
            )
        return (
            f"background:{card_bg};"
            f"border-radius:24px;"
            f"margin:12px auto;"
            f"max-width:860px;"
            f"overflow:hidden;"
            f"box-shadow:"
            f"0 1px 2px rgba(0,0,0,0.07),"
            f"0 4px 8px rgba(0,0,0,0.07),"
            f"0 12px 24px rgba(0,0,0,0.09),"
            f"0 24px 48px rgba(0,0,0,0.06);"
        )

    def accent_stripe_html(accent_hex, scheme=None):
        if scheme == "Low Stimulation":
            return ""
        return (
            f"<div style='"
            f"height:6px;"
            f"background:linear-gradient(90deg,{accent_hex},{accent_hex}99,{accent_hex}33);"
            f"'></div>"
        )

    def emoji_strip_html(accent_hex, topic_emoji, scheme=None, count=9):
        if scheme == "Low Stimulation":
            return ""
        sizes = [18, 20, 24, 26, 28, 26, 24, 20, 18]
        sizes = (sizes * ((count // len(sizes)) + 1))[:count]
        anim = (
            "<style>"
            "@keyframes fcmEmojiFloat{"
            "0%,100%{transform:translateY(0)}"
            "50%{transform:translateY(-4px)}"
            "}"
            "@media(prefers-reduced-motion:reduce){"
            ".fcm-strip-emoji{animation:none!important}"
            "}"
            "</style>"
        )
        emojis_row = "".join(
            f"<span class='fcm-strip-emoji' style='"
            f"font-size:{sz}px;line-height:1;display:inline-block;"
            f"animation:fcmEmojiFloat {1.8 + i*0.15:.2f}s ease-in-out infinite;"
            f"animation-delay:{i*0.12:.2f}s;"
            f"'>{twemojify(topic_emoji)}</span>"
            for i, sz in enumerate(sizes)
        )
        return (
            f"{anim}"
            f"<div style='"
            f"background:linear-gradient(135deg,{accent_hex},{accent_hex}cc);"
            f"padding:14px 20px;"
            f"display:flex;justify-content:space-around;align-items:center;gap:4px;"
            f"'>"
            f"{emojis_row}"
            f"</div>"
        )

    def card_body_style(scheme=None):
        if scheme == "Low Stimulation":
            return "padding:28px 28px;"
        return "padding:36px 40px;"

    # Single-card paginated view
    total_cards = len(flashcards)

    if st.session_state.current_card_idx >= total_cards:
        st.session_state.current_card_idx = 0
    idx = st.session_state.current_card_idx

    card = flashcards[idx]
    is_flipped = st.session_state.card_flipped.get(idx, False)
    emoji = card.get('emoji', '💡')
    deco = [DECORATION_EMOJIS[(idx + i*2) % len(DECORATION_EMOJIS)] for i in range(4)]
    text_color = card_colors['text']
    label_color = card_colors['label']
    accent_color = card_colors.get('accent', label_color)

    scheme_name = st.session_state.colour_scheme
    card_bg = card_colors.get('card_bg', '#FFFEF9')
    outer_style = card_outer_style(accent_color, card_bg, scheme=scheme_name)
    body_style = card_body_style(scheme=scheme_name)
    accent_stripe = accent_stripe_html(accent_color, scheme=scheme_name)
    top_strip = emoji_strip_html(accent_color, emoji, scheme=scheme_name)
    bottom_strip = top_strip

    st.markdown(
        f"<p style='text-align:center; color:{label_color}; font-weight:700; letter-spacing:2px; margin:28px 0 8px 0; font-size:0.85em;'>✨ CARD {idx + 1} OF {total_cards} ✨</p>",
        unsafe_allow_html=True
    )

    has_image = (
        show_images
        and idx in st.session_state.card_images
        and st.session_state.card_images[idx] is not None
    )
    img_url = st.session_state.card_images.get(idx) if has_image else None

    if show_images and idx not in st.session_state.card_images:
        with st.spinner("✨ Preparing..."):
            search_term = card.get('image_search', card['title'])
            st.session_state.card_images[idx] = search_wikipedia_image(search_term)
            has_image = st.session_state.card_images[idx] is not None
            img_url = st.session_state.card_images[idx]

    img_alt = f"Illustration related to the topic: {card['title']}"

    card_bg_color = card_bg
    sticker_size = 48
    if has_image and img_url:
        sticker_html = (
            f"<div style='position:absolute; top:-10px; right:-10px; "
            f"width:{sticker_size}px; height:{sticker_size}px; border-radius:50%; "
            f"background:{accent_color}; display:flex; align-items:center; "
            f"justify-content:center; font-size:26px; line-height:1; "
            f"border:3px solid {card_bg_color}; "
            f"box-shadow:0 3px 10px rgba(0,0,0,0.30); z-index:2;' "
            f"aria-hidden='true'>{twemojify(emoji)}</div>"
        )
        # Polaroid: white border, slight rotation, drop shadow
        image_frame_style = (
            f"padding:10px 10px 28px 10px;"
            f"background:#ffffff;"
            f"box-shadow:0 4px 16px rgba(0,0,0,0.18),0 1px 3px rgba(0,0,0,0.12);"
            f"border-radius:3px;"
            f"transform:rotate(-1.2deg);"
            f"display:inline-block;"
        )
    else:
        sticker_html = ""
        image_frame_style = ""

    if is_flipped:
        fact_lines = []
        for fact in card['facts']:
            if isinstance(fact, dict):
                fact_emoji = fact.get('emoji', '*')
                fact_text = fact.get('text', '')
            else:
                fact_emoji = '*'
                fact_text = str(fact)
            fact_lines.append(
                f"<div style='display:flex; align-items:flex-start; gap:14px; "
                f"margin:12px 0; padding-left:4px;'>"
                f"<span style='flex:0 0 auto; width:2em; font-size:1.2em; "
                f"line-height:var(--line-height); text-align:center;' aria-hidden='true'>{twemojify(fact_emoji)}</span>"
                f"<span style='flex:1 1 auto; color:{text_color}; "
                f'font-family:"{st.session_state.font_style}", sans-serif; '
                f"font-size:{st.session_state.text_size}px; line-height:var(--line-height); "
                f"text-align:left;'>{fact_text}</span>"
                f"</div>"
            )
        facts_html = (
            "<div style='max-width:85ch; margin:0 auto;'>"
            + "".join(fact_lines)
            + "</div>"
        )

        if has_image and img_url:
            image_block = (
                f"<div style='text-align:center; margin:0 0 30px 0;'>"
                f"<div style='position:relative; display:inline-block; {image_frame_style}'>"
                f"<img src='{img_url}' alt='{img_alt}' "
                f"style='max-width:100%; max-height:300px; width:auto; height:auto; "
                f"border-radius:2px; display:block;' />"
                f"{sticker_html}"
                f"</div>"
                f"<p style='font-size:0.78em; color:{label_color}; margin:14px 0 0 0; "
                f"letter-spacing:1px; font-weight:600; text-transform:uppercase;'>{card['title']}</p>"
                f"</div>"
            )
        else:
            image_block = ""

        st.markdown(
f"""<div style='{outer_style}'>
{accent_stripe}
{top_strip}
<div style='{body_style}'>
<p style='text-align:center; color:{label_color}; font-weight:800; letter-spacing:3px; font-size:0.8em; margin:0 0 20px 0; text-transform:uppercase;'>{deco[0]} KEY FACTS {deco[1]}</p>
{image_block}
{facts_html}
</div>
{bottom_strip}
</div>""",
            unsafe_allow_html=True
        )
    else:
        if has_image and img_url:
            anchor_block = (
                f"<div style='text-align:center; margin:0 0 24px 0;'>"
                f"<div style='position:relative; display:inline-block; {image_frame_style}'>"
                f"<img src='{img_url}' alt='{img_alt}' "
                f"style='max-width:300px; max-height:300px; width:auto; height:auto; "
                f"border-radius:2px; display:block;' />"
                f"{sticker_html}"
                f"</div>"
                f"</div>"
            )
        else:
            anchor_block = (
                f"<div style='font-size:110px; line-height:1; margin-bottom:24px;' "
                f"role='img' aria-label='{img_alt}'>{twemojify(emoji)}</div>"
            )

        title_size = max(st.session_state.text_size + 14, 30)
        st.markdown(
f"""<div style='{outer_style}'>
{accent_stripe}
{top_strip}
<div style='{body_style} text-align:center;'>
{anchor_block}
<p style='color:{label_color}; font-weight:800; letter-spacing:3px; font-size:0.78em; margin:0 0 14px 0; text-transform:uppercase;'>TOPIC</p>
<div style='color:{text_color}; font-family:"{st.session_state.font_style}", sans-serif; font-size:{title_size}px; font-weight:800; line-height:1.25; text-shadow:0 2px 8px rgba(0,0,0,0.10); padding:0 16px;'>{card['title']}</div>
<p style='font-size:30px; opacity:0.35; margin-top:28px; letter-spacing:14px;' aria-hidden='true'>{deco[0]} {deco[1]} {deco[2]} {deco[3]}</p>
</div>
{bottom_strip}
</div>""",
            unsafe_allow_html=True
        )

    _, btn_m, _ = st.columns([1, 1, 1])
    with btn_m:
        flip_text = "🔄 Show Topic" if is_flipped else "🔄 Reveal Facts"
        if st.button(flip_text, key=f"flip_{idx}", use_container_width=True):
            st.session_state.card_flipped[idx] = not is_flipped
            st.rerun()

    # PNG download for single card
    _, dl_single, _ = st.columns([1, 1, 1])
    with dl_single:
        wiki_bytes = fetch_image_bytes(img_url) if img_url else None
        png_bytes = render_card_to_png(
            card=card,
            colors=card_colors,
            idx=idx,
            total=total_cards,
            wiki_image_bytes=wiki_bytes,
            page_bg_hex=PAGE_BG_MAP.get(st.session_state.colour_scheme, "#E8F1F5"),
        )
        safe_title = re.sub(r"[^a-zA-Z0-9_-]+", "_", card["title"]).strip("_") or "card"
        st.download_button(
            label="📸 Download This Card",
            data=png_bytes,
            file_name=f"card_{idx + 1}_{safe_title}.png",
            mime="image/png",
            key=f"dl_single_{idx}",
            use_container_width=True,
        )

    # Navigation
    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
    nav_prev, nav_info, nav_next = st.columns([1, 1.2, 1])

    with nav_prev:
        if st.button(
            "◀ Previous",
            key="nav_prev_btn",
            disabled=(idx == 0),
            use_container_width=True,
        ):
            st.session_state.current_card_idx = max(0, idx - 1)
            st.rerun()

    with nav_info:
        st.markdown(
            f"<p style='text-align:center; color:{label_color}; font-weight:700; "
            f"margin: 10px 0 0 0; font-size:0.95em;'>Card {idx + 1} of {total_cards}</p>",
            unsafe_allow_html=True
        )

    with nav_next:
        if st.button(
            "Next ▶",
            key="nav_next_btn",
            disabled=(idx == total_cards - 1),
            use_container_width=True,
        ):
            st.session_state.current_card_idx = min(total_cards - 1, idx + 1)
            st.rerun()

    
    st.markdown("---")
    st.markdown("### 📥 Download All Cards")

    def _format_fact(fact):
        if isinstance(fact, dict):
            return f"  {fact.get('emoji', '*')} {fact.get('text', '')}"
        return f"  * {fact}"

    download_text = "\n\n".join([
        f"TOPIC: {c['title']}\nFACTS:\n" + "\n".join([_format_fact(f) for f in c['facts']])
        for c in flashcards
    ])

    active_page_bg = PAGE_BG_MAP.get(st.session_state.colour_scheme, "#E8F1F5")
    zip_cache_key = (
        flashcards[0]["title"] if flashcards else "",
        len(flashcards),
        st.session_state.colour_scheme,
    )
    zip_bytes = build_cards_zip(
        flashcards,
        st.session_state.card_images,
        card_colors,
        active_page_bg,
        zip_cache_key,
    )

    dl_left, dl_right = st.columns(2)
    with dl_left:
        st.download_button(
            label="📦 All Cards (ZIP of PNGs)",
            data=zip_bytes,
            file_name="flashcards.zip",
            mime="application/zip",
            key="dl_all_zip",
            use_container_width=True,
        )
    with dl_right:
        st.download_button(
            label="📝 Text File",
            data=download_text,
            file_name="study_cards.txt",
            mime="text/plain",
            key="dl_all_text",
            use_container_width=True,
        )

st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
