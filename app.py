# app.py - main flashcard app (with non‑breaking API key validation)

import os
import re
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

try:
    if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

# --- GENTLE API KEY VALIDATION (no st.stop) ---
api_key = os.getenv("ANTHROPIC_API_KEY")
api_key_valid = bool(api_key and api_key.strip())
# ------------------------------------------------

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
    MIN_FONT_SIZE, MAX_FONT_SIZE, DEFAULT_FONT_SIZE
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
MAX_CHARS = 24000

PAGE_BG_MAP = {
    "Soft Blue":       "#E8F1F5",
    "Pale Lavender":   "#F5E8F5",
    "Pale Mint":       "#E8F5F1",
    "Low Stimulation": "#F2F2EC",
}

render_header(APP_TITLE, APP_SUBTITLE, st.session_state.text_size, st.session_state.colour_scheme)
st.markdown("<div style='margin-bottom: 28px;'></div>", unsafe_allow_html=True)
render_mobile_settings_hint()

# --- Sidebar (unchanged) ---
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    # Show warning if API key is missing
    if not api_key_valid:
        st.error(
            "❌ **Anthropic API key missing**\n\n"
            "Flashcards cannot be generated.\n\n"
            "**Local:** Create a `.env` file with:\n"
            "`ANTHROPIC_API_KEY=your-key-here`\n\n"
            "**Streamlit Cloud:** Add to `.streamlit/secrets.toml`:\n"
            "`ANTHROPIC_API_KEY = \"your-key-here\"`"
        )
    
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

    colour_options = ["Soft Blue", "Pale Lavender", "Pale Mint", "Low Stimulation"]
    if st.session_state.colour_scheme not in colour_options:
        st.session_state.colour_scheme = "Soft Blue"
    new_colour = st.selectbox("Colour Scheme", colour_options, index=colour_options.index(st.session_state.colour_scheme), key="colour_selectbox")
    if new_colour != st.session_state.colour_scheme:
        st.session_state.colour_scheme = new_colour
        st.rerun()
    
    show_images = st.checkbox("Show Images", value=True, key="show_images_check", help="Show relevant images from Wikipedia on flipped cards")
    
    st.markdown("---")
    st.caption("💡 These settings adjust the whole app. Change them any time - your cards won't disappear.")

# --- Main content ---
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

st.caption("⚠️ Your text is sent to Anthropic's AI and Wikipedia to make flashcards. Please don't paste anything confidential.")

_, btn, _ = st.columns([1, 1.2, 1])
with btn:
    # Disable button if API key is missing
    make_disabled = not api_key_valid
    if st.button("✨ Make Flashcard", use_container_width=True, key="make_flashcard_btn", disabled=make_disabled):
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

# If key is missing, show a persistent warning in the main area too
if not api_key_valid:
    st.warning(
        "⚠️ **Cannot generate flashcards** – Anthropic API key is missing.\n\n"
        "Please add your key to a `.env` file or Streamlit secrets and restart the app."
    )

if not st.session_state.flashcard_generated:
    st.markdown(
        "<p style='text-align:center; opacity:0.75; margin-top:20px;'>👆 Paste some text above to get started!</p>",
        unsafe_allow_html=True
    )

# --- The rest of your flashcard display (unchanged from your original) ---
# (I'm truncating here for brevity – keep your existing flashcard rendering code)
# ... (paste your original flashcard display logic here) ...

# --- feedback box ---
st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
render_feedback_box(FEEDBACK_URL, st.session_state.colour_scheme)
