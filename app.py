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
    search_wikipedia_image, render_header,
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
    "active_reading_level": None,
    "pending_reading_level": None,
    "trigger_regenerate": False,
    "image_search_cache": {},
    "dialog_answered": False,
    "stored_user_text": "",
    "show_level_banner": False,
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
MAX_CHARS = 70000  # <-- changed from 24000 to 70000

PAGE_BG_MAP = {
    name: palette["bg"]
    for group in COLOR_SCHEMES.values()
    for name, palette in group.items()
}

render_header(APP_TITLE, APP_SUBTITLE, st.session_state.text_size, st.session_state.colour_scheme)
st.markdown("<div style='margin-bottom: 28px;'></div>", unsafe_allow_html=True)
render_mobile_settings_hint(st.session_state.colour_scheme)

def _render_level_modal(pending_level):
    """Inline modal — fully controlled via session state, no st.dialog."""
    palette = _get_scheme_palette_safe()
    accent  = palette["accent"]
    bg      = palette["card_bg"]
    text    = palette["text"]

    # Overlay + centred card using fixed positioning via CSS injected into the page
    st.markdown(f"""
<style>
.fcm-overlay {{
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.45);
    z-index: 9998;
    display: flex; align-items: center; justify-content: center;
}}
.fcm-modal {{
    background: {bg};
    border-radius: 16px;
    padding: 32px 28px 24px;
    max-width: 420px; width: 90%;
    box-shadow: 0 8px 40px rgba(0,0,0,0.3);
    z-index: 9999;
    animation: fcmPop 0.18s ease-out;
}}
@keyframes fcmPop {{
    from {{ transform: scale(0.92); opacity: 0; }}
    to   {{ transform: scale(1);    opacity: 1; }}
}}
.fcm-modal-title {{
    font-size: 1.25em; font-weight: 700;
    color: {text}; margin: 0 0 12px 0;
}}
.fcm-modal-body {{
    font-size: 1em; color: {text};
    opacity: 0.85; margin: 0 0 24px 0;
    line-height: 1.6;
}}
.fcm-modal-level {{
    color: {accent}; font-weight: 700;
}}
</style>
<div class="fcm-overlay">
  <div class="fcm-modal">
    <p class="fcm-modal-title">Change reading level?</p>
    <p class="fcm-modal-body">
      This will create a new deck of cards at
      <span class="fcm-modal-level">{pending_level.split("(")[0].strip()}</span>
      level.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

    col_no, col_yes = st.columns(2)
    with col_no:
        if st.button("No, keep current cards", use_container_width=True, key="modal_no"):
            st.session_state.pending_reading_level = None
            st.rerun()
    with col_yes:
        if st.button("Yes, generate new deck ✨", use_container_width=True, key="modal_yes"):
            st.session_state.active_reading_level = pending_level
            st.session_state.pending_reading_level = None
            st.session_state.trigger_regenerate = True
            st.rerun()


def _get_scheme_palette_safe():
    """Get the current colour palette without importing inside a function."""
    from config import COLOR_SCHEMES
    scheme = st.session_state.get("colour_scheme", "Soft Blue")
    for group in COLOR_SCHEMES.values():
        if scheme in group:
            return group[scheme]
    return COLOR_SCHEMES["Accessibility"]["Soft Blue"]

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    reading_level_options = list(READING_LEVELS.keys())
    # Always show the confirmed active level in the widget — this makes No/X
    # snap the dropdown back automatically since we control the index.
    active_level = st.session_state.active_reading_level or reading_level_options[0]
    if active_level not in reading_level_options:
        active_level = reading_level_options[0]
    selected_level = st.selectbox(
        "Reading Level",
        reading_level_options,
        index=reading_level_options.index(active_level),
        key="reading_level_select",
    )
    st.caption("📖 Each level creates a new set of cards.")
    # Only set pending if: cards exist, something genuinely changed, and no
    # dialog is already open (prevents re-triggering on every rerun).
    if (selected_level != active_level
            and st.session_state.flashcard_generated
            and not st.session_state.pending_reading_level):
        st.session_state.pending_reading_level = selected_level
        st.rerun()
    reading_level = active_level

    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)

    safe_font = st.session_state.font_style if st.session_state.font_style in FONT_OPTIONS else "Verdana"
    new_font = st.selectbox("Font Style", FONT_OPTIONS, index=FONT_OPTIONS.index(safe_font), key="font_selectbox")
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

# --- Show reading level modal if needed ---
if st.session_state.pending_reading_level:
    _render_level_modal(st.session_state.pending_reading_level)

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

def _run_generation(level_key, show_imgs, reuse_images=False):
    """Shared card generation logic used by both the button and auto-regenerate.

    reuse_images=True: carry over any image whose image_search term matches a
    card in the previous deck (same topic at a different reading level).
    """
    level_code = READING_LEVELS[level_key]
    # Snapshot the previous image cache keyed by search term before clearing
    prev_cache = {}
    if reuse_images and st.session_state.image_search_cache:
        prev_cache = dict(st.session_state.image_search_cache)

    st.session_state.card_images = {}
    st.session_state.card_flipped = {}
    st.session_state.current_card_idx = 0

    new_cards = None
    _text_to_use = st.session_state.stored_user_text or user_text
    with st.spinner(f"🤖 AI is creating {level_key.split('(')[0].strip()} flashcards..."):
        new_cards = generate_flashcards_from_llm(_text_to_use, reading_level=level_code)
        if new_cards:
            st.session_state.flashcards = new_cards
            st.session_state.flashcard_generated = True

    if new_cards and show_imgs:
        # Populate card_images — reuse from prev_cache where search term matches
        needs_fetch = []
        for i, card in enumerate(new_cards):
            search_term = card.get('image_search', card['title'])
            if search_term in prev_cache:
                st.session_state.card_images[i] = prev_cache[search_term]
            else:
                needs_fetch.append((i, search_term))

        if needs_fetch:
            with st.spinner("🖼️ Finding pictures for each card..."):
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=5) as pool:
                    results = list(pool.map(
                        lambda item: (item[0], item[1], search_wikipedia_image(item[1])),
                        needs_fetch
                    ))
                for i, search_term, url in results:
                    st.session_state.card_images[i] = url

        # Update the persistent search-term → url cache for future reuse
        st.session_state.image_search_cache = {
            card.get('image_search', card['title']): st.session_state.card_images.get(i)
            for i, card in enumerate(new_cards)
            if st.session_state.card_images.get(i) is not None
        }

# --- Auto-regenerate after dialog confirmation ---
if st.session_state.trigger_regenerate:
    st.session_state.trigger_regenerate = False
    st.session_state.show_level_banner = True
    _regen_text = st.session_state.stored_user_text or user_text
    if _regen_text.strip() and len(_regen_text.split()) >= 20:
        _run_generation(st.session_state.active_reading_level, show_images, reuse_images=True)
    else:
        st.warning("⚠️ Please enter or upload some text first, then change the reading level.")

# --- Reading level change banner (shows briefly after level changes) ---
if st.session_state.get("show_level_banner"):
    new_lvl = st.session_state.active_reading_level or ""
    lvl_label = new_lvl.split("(")[0].strip()
    palette = _get_scheme_palette_safe()
    accent = palette["accent"]
    st.markdown(f"""
<style>
@keyframes fcmTypewriter {{
    from {{ width: 0; }}
    to   {{ width: 100%; }}
}}
@keyframes fcmFadeSlide {{
    0%   {{ opacity: 0; transform: translateY(-8px); }}
    15%  {{ opacity: 1; transform: translateY(0); }}
    75%  {{ opacity: 1; transform: translateY(0); }}
    100% {{ opacity: 0; transform: translateY(-8px); }}
}}
.fcm-level-banner {{
    text-align: center;
    padding: 10px 16px;
    border-radius: 10px;
    background: {accent}22;
    border: 1px solid {accent}55;
    margin-bottom: 12px;
    animation: fcmFadeSlide 2.2s ease forwards;
    font-weight: 600;
    color: {accent};
    overflow: hidden;
}}
.fcm-level-typewriter {{
    display: inline-block;
    overflow: hidden;
    white-space: nowrap;
    border-right: 2px solid {accent};
    animation: fcmTypewriter 0.6s steps(30) 0.3s forwards,
               fcmBlink 0.5s step-end infinite;
    width: 0;
}}
@keyframes fcmBlink {{
    50% {{ border-color: transparent; }}
}}
</style>
<div class="fcm-level-banner">
    📖 Reading level changed to
    <span class="fcm-level-typewriter">{lvl_label}</span>
</div>
""", unsafe_allow_html=True)
    st.session_state.show_level_banner = False

_, btn, _ = st.columns([1, 1.2, 1])
with btn:
    if st.button("✨ Make Flashcard", use_container_width=True, key="make_flashcard_btn"):
        if not user_text.strip():
            st.warning("⚠️ Please enter or upload some text first!")
        elif word_count < 20:
            st.warning("⚠️ Please add a bit more text (at least 20 words) so the AI has enough to work with.")
        else:
            st.session_state.active_reading_level = reading_level
            st.session_state.stored_user_text = user_text
            st.session_state.image_search_cache = {}
            _run_generation(reading_level, show_images, reuse_images=False)

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

    img_alt = f"Illustration related to the topic: {_safe(card['title'])}"

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
                f"text-align:left;'>{_safe(fact_text)}</span>"
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
                f"<p style='font-size:0.8em; color:{label_color}; margin:8px 0 0 0;'>{_safe(card['title'])}</p>"
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
<div style='color:{text_color}; font-family:"{st.session_state.font_style}", sans-serif; font-size:{max(st.session_state.text_size + 10, 26)}px; font-weight:700;'>{_safe(card['title'])}</div>
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
