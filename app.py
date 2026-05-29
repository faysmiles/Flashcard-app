# app.py - main flashcard app (DeepSeek + Pollinations + Supabase – no Anthropic)

import os
import re
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# Anthropic key handling removed – you now use DeepSeek, Pollinations, Supabase

config_dir = os.path.expanduser("~/.streamlit")
config_file = os.path.join(config_dir, "config.toml")
if not os.path.exists(config_file):
    os.makedirs(config_dir, exist_ok=True)
    with open(config_file, "w") as f:
        f.write("""[theme]
primaryColor = "#3A7CA5"
backgroundColor = "#E8F1F5"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#1C3A42"
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
    MIN_FONT_SIZE, MAX_FONT_SIZE, DEFAULT_FONT_SIZE, COLOR_SCHEMES,
)
from utils import (
    apply_styles, extract_text_from_file,
    generate_flashcards_from_llm, get_card_colors,
    search_wikipedia_image, render_header, render_feedback_box,
    render_card_to_png, fetch_image_bytes, build_cards_zip,
    render_mobile_settings_hint,
)

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

FEEDBACK_URL = "https://docs.google.com/forms/d/e/1FAIpQLSftcBkHjYju-nNZ0uENPLc1CNSLTrEV3WBR0PenubeZALjypw/viewform"
DECORATION_EMOJIS = ['✨', '⭐', '💫', '🌟', '🎯', '📚', '💡', '🎨']
MAX_CHARS = 70000  # <-- changed from 24000 to 70000

PAGE_BG_MAP = {
    name: palette["bg"]
    for group in COLOR_SCHEMES.values()
    for name, palette in group.items()
}

render_header(APP_TITLE, APP_SUBTITLE, st.session_state.text_size, st.session_state.colour_scheme)
st.markdown("<div style='margin-bottom: 28px;'></div>", unsafe_allow_html=True)
render_mobile_settings_hint(st.session_state.colour_scheme)

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
        help="Space between lines of text.",
    )
    if SPACING_OPTIONS[new_spacing_key] != st.session_state.line_spacing:
        st.session_state.line_spacing = SPACING_OPTIONS[new_spacing_key]
        st.rerun()

    colour_options = [name for group in COLOR_SCHEMES.values() for name in group]
    if st.session_state.colour_scheme not in colour_options:
        st.session_state.colour_scheme = "Soft Blue"
    new_colour = st.selectbox("Colour Scheme", colour_options, index=colour_options.index(st.session_state.colour_scheme), key="colour_selectbox")
    if new_colour != st.session_state.colour_scheme:
        st.session_state.colour_scheme = new_colour
        st.rerun()
    
    show_images = st.checkbox("Show Images", value=True, key="show_images_check", help="Show relevant images from Wikipedia on flipped cards")
    
    st.markdown("---")
    st.caption("💡 These settings adjust the whole app. Change them any time - your cards won't disappear.")

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
    st.info(f"ℹ️ Your text is quite long - we'll use the first {MAX_CHARS:,} characters.")
    user_text = user_text[:MAX_CHARS]

word_count = len(user_text.split()) if user_text else 0
st.caption(f"📝 {word_count} words")
st.caption("⚠️ Your text is sent to DeepSeek AI and Pollinations image service to create flashcards. Please don't paste anything confidential.")

_, btn, _ = st.columns([1, 1.2, 1])
with btn:
    if st.button("✨ Make Flashcard", use_container_width=True, key="make_flashcard_btn"):
        if not user_text.strip():
            st.warning("⚠️ Please enter or upload some text first!")
        elif word_count < 20:
            st.warning("⚠️ Please add a bit more text (at least 20 words) so the AI has enough to work with.")
        else:
            level_code = READING_LEVELS[reading_level]
            st.session_state.card_images = {}
            st.session_state.card_flipped = {}
            st.session_state.current_card_idx = 0
            
            with st.spinner(f"🤖 AI is creating {reading_level.split('(')[0].strip()} flashcards..."):
                new_cards = generate_flashcards_from_llm(user_text, reading_level=level_code)
                if new_cards:
                    st.session_state.flashcards = new_cards
                    st.session_state.flashcard_generated = True
            
            if new_cards and show_images:
                with st.spinner("🖼️ Finding pictures for each card..."):
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
    
    def card_outer_style(accent_hex, scheme=None):
        base = (
            f"background: #FFFEF9;"
            f"border-radius: 18px;"
            f"margin: 8px auto;"
            f"max-width: 620px;"
            f"box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);"
            f"overflow: hidden;"
        )
        if scheme == "Low Stimulation":
            return base + f"border: 2px solid {accent_hex};"
        return base

    def emoji_strip_html(accent_hex, topic_emoji, scheme=None, count=7):
        if scheme == "Low Stimulation":
            return ""
        emojis_row = "".join(
            f"<span style='font-size:20px; line-height:1;'>{topic_emoji}</span>"
            for _ in range(count)
        )
        return (
            f"<div style='background:{accent_hex}; padding:10px 16px; "
            f"display:flex; justify-content:space-around; align-items:center;'>"
            f"{emojis_row}"
            f"</div>"
        )

    def card_body_style(scheme=None):
        if scheme == "Low Stimulation":
            return "padding: 24px 22px;"
        return "padding: 28px 24px;"

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
    outer_style = card_outer_style(accent_color, scheme=scheme_name)
    body_style = card_body_style(scheme=scheme_name)
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
        with st.spinner(f"🖼️ Finding picture for card {idx + 1}..."):
            search_term = card.get('image_search', card['title'])
            st.session_state.card_images[idx] = search_wikipedia_image(search_term)
            has_image = st.session_state.card_images[idx] is not None
            img_url = st.session_state.card_images[idx]

    img_alt = f"Illustration related to the topic: {card['title']}"

    card_bg_color = "#FFFEF9"
    sticker_size = 44
    if has_image:
        sticker_html = (
            f"<div style='position:absolute; top:-8px; right:-8px; "
            f"width:{sticker_size}px; height:{sticker_size}px; border-radius:50%; "
            f"background:{accent_color}; display:flex; align-items:center; "
            f"justify-content:center; font-size:24px; line-height:1; "
            f"border:3px solid {card_bg_color}; "
            f"box-shadow:0 2px 8px rgba(0,0,0,0.25); z-index:2;' "
            f"aria-hidden='true'>{emoji}</div>"
        )
        image_frame_style = (
            f"box-shadow:0 0 0 4px {accent_color}, "
            f"0 4px 12px rgba(0,0,0,0.12);"
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
                f"line-height:var(--line-height); text-align:center;' aria-hidden='true'>{fact_emoji}</span>"
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

        if has_image:
            image_block = (
                f"<div style='text-align:center; margin:0 0 24px 0;'>"
                f"<div style='position:relative; display:inline-block;'>"
                f"<img src='{img_url}' alt='{img_alt}' "
                f"style='max-width:100%; max-height:320px; width:auto; height:auto; "
                f"border-radius:12px; {image_frame_style} display:block;' />"
                f"{sticker_html}"
                f"</div>"
                f"<p style='font-size:0.8em; color:{label_color}; margin:8px 0 0 0;'>{card['title']}</p>"
                f"</div>"
            )
        else:
            image_block = ""

        st.markdown(
f"""<div style='{outer_style}'>
{top_strip}
<div style='{body_style}'>
<p style='text-align:center; color:{label_color}; font-weight:800; letter-spacing:3px; font-size:0.9em; margin:0 0 16px 0;'>{deco[0]} KEY FACTS {deco[1]}</p>
{image_block}
{facts_html}
</div>
{bottom_strip}
</div>""",
            unsafe_allow_html=True
        )
    else:
        if has_image:
            anchor_block = (
                f"<div style='text-align:center; margin:0 0 20px 0;'>"
                f"<div style='position:relative; display:inline-block;'>"
                f"<img src='{img_url}' alt='{img_alt}' "
                f"style='max-width:280px; max-height:280px; width:auto; height:auto; "
                f"border-radius:14px; {image_frame_style} display:block;' />"
                f"{sticker_html}"
                f"</div>"
                f"</div>"
            )
        else:
            anchor_block = (
                f"<div style='font-size:100px; line-height:1; margin-bottom:20px;' "
                f"role='img' aria-label='{img_alt}'>{emoji}</div>"
            )

        st.markdown(
f"""<div style='{outer_style}'>
{top_strip}
<div style='{body_style} text-align:center;'>
{anchor_block}
<p style='color:{label_color}; font-weight:800; letter-spacing:3px; font-size:0.85em; margin:0 0 16px 0;'>TOPIC</p>
<div style='color:{text_color}; font-family:"{st.session_state.font_style}", sans-serif; font-size:{max(st.session_state.text_size + 10, 26)}px; font-weight:700;'>{card['title']}</div>
<p style='font-size:28px; opacity:0.4; margin-top:24px; letter-spacing:10px;' aria-hidden='true'>{deco[0]} {deco[1]} {deco[2]} {deco[3]}</p>
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

    # --- single-card PNG download ---
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

    # --- prev / counter / next navigation ---
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

# --- feedback box at bottom of page ---
st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
render_feedback_box(FEEDBACK_URL, st.session_state.colour_scheme)
