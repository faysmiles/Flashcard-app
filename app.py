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

# auto-create the theme config file
config_dir = os.path.expanduser("~/.streamlit")
config_file = os.path.join(config_dir, "config.toml")
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
    search_wikipedia_image
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
    "flashcards_direct": None,
    "final_input_text": "",
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

# --- header ---
header_left, header_right = st.columns([2, 1], gap="medium")

with header_left:
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #D4A017 0%, #E8B923 50%, #DAA520 100%); padding: 28px 26px; border-radius: 12px; box-shadow: 0 4px 16px rgba(218, 165, 32, 0.25); height: 100%; box-sizing: border-box;'>
        <h1 style='font-size: 2em; font-weight: 800; color: #FFFFFF; margin: 0; line-height: 1.1; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);'>💡 {APP_TITLE}</h1>
        <p style='font-size: 0.95em; color: rgba(255, 255, 255, 0.95); margin: 10px 0 0 0;'>{APP_SUBTITLE}</p>
    </div>
    """, unsafe_allow_html=True)

with header_right:
    st.markdown(f"""
    <div style='text-align:center; padding:20px 16px; background:rgba(255, 107, 107, 0.08); border:2px solid rgba(255, 107, 107, 0.2); border-radius:12px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center;'>
        <p style='margin:0 0 8px 0; font-size:0.95em; font-weight:700; color:#2C2416;'>💬 Help improve this app!</p>
        <p style='margin:0 0 12px 0; font-size:0.8em; color:#5C5246;'>Your feedback supports our research</p>
        <a href='{FEEDBACK_URL}' target='_blank' style='display:inline-block; padding:10px 20px; background:#FF6B6B; color:white; text-decoration:none; border-radius:8px; font-weight:700; font-size:0.9em;'>📝 Take Survey</a>
    </div>
    """, unsafe_allow_html=True)

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
    
    make_pictures = st.checkbox("Show Images", value=True, key="make_pictures_check", help="Show relevant images from Wikipedia on flipped cards")

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
    
    # show a little word count
    word_count = len(user_text.split()) if user_text else 0
    st.caption(f"📝 {word_count} words")
    
    # generate button
    btn1, btn2, btn3 = st.columns([1, 1.2, 1])
    with btn2:
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
                    flashcards = generate_flashcards_from_llm(user_text, reading_level=level_code)
                    if flashcards:
                        st.session_state.flashcards_direct = flashcards
                        st.session_state.final_input_text = user_text
                        st.session_state.flashcard_generated = True
    
    # --- show the flashcards ---
    if st.session_state.flashcard_generated and st.session_state.flashcards_direct:
        flashcards = st.session_state.flashcards_direct
        
        # make sure we have flip state for each card
        for i in range(len(flashcards)):
            if i not in st.session_state.card_flipped:
                st.session_state.card_flipped[i] = False
        
        card_colors = get_card_colors(st.session_state.colour_scheme)
        
        st.markdown("---")
        
        # header + regenerate button
        hdr_l, hdr_r = st.columns([3, 1])
        with hdr_l:
            st.markdown(f"### 📚 Your Flashcards ({len(flashcards)} cards)")
        with hdr_r:
            if st.button("🔁 Regenerate", use_container_width=True, key="regenerate_btn", help="Not happy with the cards? Make new ones from the same text."):
                level_code = READING_LEVELS[reading_level]
                st.session_state.card_images = {}
                st.session_state.card_flipped = {}
                with st.spinner("🤖 Making new flashcards..."):
                    new_cards = generate_flashcards_from_llm(st.session_state.final_input_text, reading_level=level_code)
                    if new_cards:
                        st.session_state.flashcards_direct = new_cards
                        st.rerun()
        
        # how many cards studied so far
        flipped_count = sum(1 for i in range(len(flashcards)) if st.session_state.card_flipped.get(i, False))
        st.markdown(
            f"<div style='padding:10px; text-align:center; background:rgba(212, 160, 23, 0.1); border-radius:8px; font-weight:700; color:#D4A017; font-size:0.9em; margin:10px 0 20px 0;'>👀 Studied: {flipped_count}/{len(flashcards)}</div>",
            unsafe_allow_html=True
        )
        
        # loop through each card
        for idx, card in enumerate(flashcards):
            is_flipped = st.session_state.card_flipped.get(idx, False)
            emoji = card.get('emoji', '💡')
            
            # pick some decoration emojis
            deco = [DECORATION_EMOJIS[(idx + i*2) % len(DECORATION_EMOJIS)] for i in range(4)]
            
            text_color = card_colors['text']
            label_color = card_colors['label']
            
            # card number
            st.markdown(
                f"<p style='text-align:center; color:{label_color}; font-weight:700; letter-spacing:2px; margin:28px 0 8px 0; font-size:0.85em;'>✨ CARD {idx + 1} OF {len(flashcards)} ✨</p>",
                unsafe_allow_html=True
            )
            
            # fetch wikipedia image when card is flipped (uses the LLM-generated search term)
            if is_flipped and make_pictures and idx not in st.session_state.card_images:
                with st.spinner(f"🖼️ Finding picture for card {idx + 1}..."):
                    search_term = card.get('image_search', card['title'])
                    image_url = search_wikipedia_image(search_term)
                    st.session_state.card_images[idx] = image_url
            
            # the actual card
            with st.container(border=True):
                if is_flipped:
                    # BACK side - show facts and maybe an image
                    has_image = (make_pictures and idx in st.session_state.card_images and st.session_state.card_images[idx] is not None)
                    
                    if has_image:
                        col_facts, col_image = st.columns([1.3, 1])
                        with col_facts:
                            st.markdown(f"<p style='text-align:center; color:{label_color}; font-weight:800; letter-spacing:3px; font-size:0.85em;'>{deco[0]} KEY FACTS {deco[1]}</p>", unsafe_allow_html=True)
                            facts_html = "".join([
                                f"<p style='color:{text_color}; font-family:{st.session_state.font_style}, sans-serif; font-size:{st.session_state.text_size}px; line-height:1.8; margin:8px 0;'>• {fact}</p>"
                                for fact in card['facts']
                            ])
                            st.markdown(facts_html, unsafe_allow_html=True)
                        with col_image:
                            st.image(st.session_state.card_images[idx], width=250)
                    else:
                        st.markdown(f"<p style='text-align:center; color:{label_color}; font-weight:800; letter-spacing:3px; font-size:0.9em; margin-top:20px;'>{deco[0]} KEY FACTS {deco[1]}</p>", unsafe_allow_html=True)
                        facts_html = "".join([
                            f"<p style='color:{text_color}; font-family:{st.session_state.font_style}, sans-serif; font-size:{st.session_state.text_size}px; line-height:1.8; margin:10px 20px;'>• {fact}</p>"
                            for fact in card['facts']
                        ])
                        st.markdown(facts_html, unsafe_allow_html=True)
                        st.markdown(f"<p style='text-align:center; font-size:24px; opacity:0.5; margin-top:20px;'>{deco[2]} {deco[3]}</p>", unsafe_allow_html=True)
                else:
                    # FRONT side - big emoji and title
                    st.markdown(f"""
                    <div style='text-align:center; padding:40px 20px;'>
                        <div style='font-size:100px; line-height:1; margin-bottom:20px;'>{emoji}</div>
                        <p style='color:{label_color}; font-weight:800; letter-spacing:3px; font-size:0.85em; margin:0 0 16px 0;'>TOPIC</p>
                        <h2 style='color:{text_color}; font-family:{st.session_state.font_style}, sans-serif; font-size:{max(st.session_state.text_size + 10, 26)}px; margin:0; font-weight:700;'>{card['title']}</h2>
                        <p style='font-size:28px; opacity:0.4; margin-top:24px; letter-spacing:10px;'>{deco[0]} {deco[1]} {deco[2]} {deco[3]}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # flip button
            btn_l, btn_m, btn_r = st.columns([1, 1, 1])
            with btn_m:
                flip_text = "🔄 Show Topic" if is_flipped else "🔄 Reveal Facts"
                if st.button(flip_text, key=f"flip_{idx}", use_container_width=True):
                    st.session_state.card_flipped[idx] = not is_flipped
                    st.rerun()
        
        # download button
        st.markdown("---")
        st.markdown("### 📥 Download Study Cards")
        dl1, dl2, dl3 = st.columns([1, 1.2, 1])
        with dl2:
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
