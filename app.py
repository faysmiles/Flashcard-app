# app.py - main flashcard app

import os
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# load api key from streamlit secrets if on cloud
try:
    if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

# create the theme config file (only if it doesn't exist yet)
config_dir = os.path.expanduser("~/.streamlit")
config_file = os.path.join(config_dir, "config.toml")
if not os.path.exists(config_file):
    os.makedirs(config_dir, exist_ok=True)
    with open(config_file, "w") as f:
        f.write("""[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#F5F1E8"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#2C2416"
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
    search_wikipedia_image, render_header, render_feedback_box
)

# page setup
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# session state - keeps track of stuff between reruns
defaults = {
    "flashcard_generated": False,
    "flashcards": None,
    "saved_text": "",
    "font_style": "Verdana",
    "text_size": DEFAULT_FONT_SIZE,
    "colour_scheme": "Cream (Dyslexia Friendly)",
    "card_flipped": {},
    "card_images": {},
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

apply_styles(st.session_state.font_style, st.session_state.text_size, st.session_state.colour_scheme)

# feedback survey link
FEEDBACK_URL = "https://docs.google.com/forms/d/e/1FAIpQLSftcBkHjYju-nNZ0uENPLc1CNSLTrEV3WBR0PenubeZALjypw/viewform"
DECORATION_EMOJIS = ['✨', '⭐', '💫', '🌟', '🎯', '📚', '💡', '🎨']
MAX_CHARS = 8000  # stop very long text from hitting AI token limits

# --- header ---
header_left, header_right = st.columns([2, 1], gap="medium")

with header_left:
    render_header(APP_TITLE, APP_SUBTITLE, st.session_state.text_size)

with header_right:
    render_feedback_box(FEEDBACK_URL)

st.markdown("<div style='margin-bottom: 28px;'></div>", unsafe_allow_html=True)

# --- main layout ---
settings_col, content_col = st.columns([0.95, 3.5], gap="medium")

# settings panel on the left
with settings_col:
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
    
    colour_options = ["Cream (Dyslexia Friendly)", "Soft Blue", "Light Grey", "Pale Lavender", "Pale Mint"]
    new_colour = st.selectbox("Colour Scheme", colour_options, index=colour_options.index(st.session_state.colour_scheme), key="colour_selectbox")
    if new_colour != st.session_state.colour_scheme:
        st.session_state.colour_scheme = new_colour
        st.rerun()
    
    show_images = st.checkbox("Show Images", value=True, key="show_images_check", help="Show relevant images from Wikipedia on flipped cards")

# main content area
with content_col:
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
    
    # if the text is really long, cut it down so the AI can handle it
    if user_text and len(user_text) > MAX_CHARS:
        st.info(f"ℹ️ Your text is quite long - we'll use the first {MAX_CHARS:,} characters to make flashcards.")
        user_text = user_text[:MAX_CHARS]
    
    # show a little word count
    word_count = len(user_text.split()) if user_text else 0
    st.caption(f"📝 {word_count} words")
    
    # privacy note - let users know where their text goes
    st.caption("⚠️ Your text is sent to Anthropic's AI and Wikipedia to make the flashcards. Please don't paste anything confidential.")
    
    # generate button
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
                
                with st.spinner(f"🤖 AI is creating {reading_level.split('(')[0].strip()} flashcards..."):
                    new_cards = generate_flashcards_from_llm(user_text, reading_level=level_code)
                    if new_cards:
                        st.session_state.flashcards = new_cards
                        st.session_state.saved_text = user_text
                        st.session_state.flashcard_generated = True
    
    # welcome message when no cards yet
    if not st.session_state.flashcard_generated:
        st.markdown(
            "<p style='text-align:center; opacity:0.75; margin-top:20px;'>👆 Paste some text above to get started!</p>",
            unsafe_allow_html=True
        )
    
    # --- show the flashcards ---
    if st.session_state.flashcard_generated and st.session_state.flashcards:
        flashcards = st.session_state.flashcards
        
        # make sure we have flip state for each card
        for i in range(len(flashcards)):
            if i not in st.session_state.card_flipped:
                st.session_state.card_flipped[i] = False
        
        card_colors = get_card_colors(st.session_state.colour_scheme)
        
        st.markdown("---")
        st.markdown(f"### 📚 Your Flashcards ({len(flashcards)} cards)")
        
        # how many cards studied so far
        flipped_count = sum(1 for i in range(len(flashcards)) if st.session_state.card_flipped.get(i, False))
        st.markdown(
            f"<div style='padding:10px; text-align:center; background:rgba(212, 160, 23, 0.1); border-radius:8px; font-weight:700; color:#D4A017; font-size:0.9em; margin:10px 0 20px 0;'>👀 Studied: {flipped_count}/{len(flashcards)}</div>",
            unsafe_allow_html=True
        )
        
        # celebrate when all cards have been flipped
        if flipped_count == len(flashcards):
            st.success("🎉 You've studied all the cards! Well done!")
        
        # shared card frame style
        card_frame = (
            "background: #FFFEF9;"
            "border-radius: 16px;"
            "border-left: 6px solid {accent};"
            "box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);"
            "padding: 28px 24px;"
            "margin: 8px 0;"
        )
        
        # loop through each card
        for idx, card in enumerate(flashcards):
            is_flipped = st.session_state.card_flipped.get(idx, False)
            emoji = card.get('emoji', '💡')
            deco = [DECORATION_EMOJIS[(idx + i*2) % len(DECORATION_EMOJIS)] for i in range(4)]
            text_color = card_colors['text']
            label_color = card_colors['label']
            accent_color = card_colors.get('accent', label_color)
            frame_style = card_frame.format(accent=accent_color)
            
            # card number
            st.markdown(
                f"<p style='text-align:center; color:{label_color}; font-weight:700; letter-spacing:2px; margin:28px 0 8px 0; font-size:0.85em;'>✨ CARD {idx + 1} OF {len(flashcards)} ✨</p>",
                unsafe_allow_html=True
            )
            
            # fetch wikipedia image when card is flipped
            if is_flipped and show_images and idx not in st.session_state.card_images:
                with st.spinner(f"🖼️ Finding picture for card {idx + 1}..."):
                    search_term = card.get('image_search', card['title'])
                    image_url = search_wikipedia_image(search_term)
                    st.session_state.card_images[idx] = image_url
            
            # build the card as pure HTML so we control the frame
            if is_flipped:
                # BACK side - facts with optional image
                has_image = (show_images and idx in st.session_state.card_images and st.session_state.card_images[idx] is not None)
                
                facts_html = "".join([
                    f"<p style='color:{text_color}; font-family:{st.session_state.font_style}, sans-serif; font-size:{st.session_state.text_size}px; line-height:1.8; margin:8px 0;'>• {fact}</p>"
                    for fact in card['facts']
                ])
                
                if has_image:
                    img_url = st.session_state.card_images[idx]
                    st.markdown(f"""
                    <div style='{frame_style}'>
                        <p style='text-align:center; color:{label_color}; font-weight:800; letter-spacing:3px; font-size:0.85em; margin:0 0 16px 0;'>{deco[0]} KEY FACTS {deco[1]}</p>
                        <div style='display:flex; gap:24px; align-items:flex-start; flex-wrap:wrap;'>
                            <div style='flex:1; min-width:200px;'>{facts_html}</div>
                            <div style='flex-shrink:0; text-align:center;'>
                                <img src='{img_url}' alt='{card["title"]}' style='width:220px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.1);' />
                                <p style='font-size:0.75em; color:{label_color}; margin-top:6px;'>{card["title"]}</p>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='{frame_style}'>
                        <p style='text-align:center; color:{label_color}; font-weight:800; letter-spacing:3px; font-size:0.9em; margin:0 0 16px 0;'>{deco[0]} KEY FACTS {deco[1]}</p>
                        {facts_html}
                        <p style='text-align:center; font-size:24px; opacity:0.5; margin-top:20px;'>{deco[2]} {deco[3]}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # FRONT side - big emoji and title
                st.markdown(f"""
                <div style='{frame_style} text-align:center; padding:40px 24px;'>
                    <div style='font-size:100px; line-height:1; margin-bottom:20px;'>{emoji}</div>
                    <p style='color:{label_color}; font-weight:800; letter-spacing:3px; font-size:0.85em; margin:0 0 16px 0;'>TOPIC</p>
                    <div style='color:{text_color}; font-family:{st.session_state.font_style}, sans-serif; font-size:{max(st.session_state.text_size + 10, 26)}px; font-weight:700;'>{card['title']}</div>
                    <p style='font-size:28px; opacity:0.4; margin-top:24px; letter-spacing:10px;'>{deco[0]} {deco[1]} {deco[2]} {deco[3]}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # flip button
            _, btn_m, _ = st.columns([1, 1, 1])
            with btn_m:
                flip_text = "🔄 Show Topic" if is_flipped else "🔄 Reveal Facts"
                if st.button(flip_text, key=f"flip_{idx}", use_container_width=True):
                    st.session_state.card_flipped[idx] = not is_flipped
                    st.rerun()
        
        # download button
        st.markdown("---")
        st.markdown("### 📥 Download Study Cards")
        _, dl_btn, _ = st.columns([1, 1.2, 1])
        with dl_btn:
            st.download_button(
                label="📥 Download as Text File",
                data="\n\n".join([
                    f"TOPIC: {card['title']}\nFACTS:\n" + "\n".join([f"  • {fact}" for fact in card['facts']])
                    for card in flashcards
                ]),
                file_name="study_cards.txt",
                mime="text/plain",
                use_container_width=True
            )
