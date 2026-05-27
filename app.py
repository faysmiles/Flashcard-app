# app.py - Main flashcard application

import os
import re
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

# Page config must be first Streamlit command
st.set_page_config(
    page_title="Flashcard Magic",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

from config import (
    APP_TITLE, APP_SUBTITLE, READING_LEVELS, FONT_OPTIONS,
    MIN_FONT_SIZE, MAX_FONT_SIZE, DEFAULT_FONT_SIZE, COLOR_SCHEMES
)
from utils import (
    apply_styles, extract_text_from_file, render_header,
    generate_flashcards_from_llm, get_card_colors, get_topic_emoji,
    search_wikipedia_image, save_deck_dialog, load_decks_from_storage,
    get_best_image, fetch_image_bytes, render_card_to_png
)

# Initialize session state
defaults = {
    "flashcard_generated": False,
    "flashcards": None,
    "font_style": "Poppins",
    "text_size": DEFAULT_FONT_SIZE,
    "colour_scheme": "Sunset Orange",
    "color_mode": "Vibrant",
    "fun_mode": True,
    "card_flipped": {},
    "card_images": {},
    "current_card_idx": 0,
    "line_spacing": 1.8,
    "show_images": True,
    "saved_decks": {},
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Load saved decks from localStorage on startup
if "decks_loaded" not in st.session_state:
    load_decks_from_storage()
    st.session_state.decks_loaded = True

MAX_CHARS = 24000
FEEDBACK_URL = "https://docs.google.com/forms/d/e/1FAIpQLSftcBkHjYju-nNZ0uENPLc1CNSLTrEV3WBR0PenubeZALjypw/viewform"

# --- Sidebar Settings ---
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    # Color mode toggle
    color_mode = st.radio(
        "🎨 Color Mode",
        ["Vibrant", "Accessibility"],
        index=0 if st.session_state.color_mode == "Vibrant" else 1,
        horizontal=True,
        help="Vibrant: bright, fun colors | Accessibility: calm, high-contrast"
    )
    if color_mode != st.session_state.color_mode:
        st.session_state.color_mode = color_mode
        st.rerun()
    
    # Color scheme picker (dynamic based on mode)
    schemes = list(COLOR_SCHEMES[st.session_state.color_mode].keys())
    current_scheme = st.session_state.colour_scheme
    if current_scheme not in schemes:
        current_scheme = schemes[0]
    
    colour_scheme = st.selectbox(
        "🎨 Color Scheme",
        schemes,
        index=schemes.index(current_scheme) if current_scheme in schemes else 0
    )
    if colour_scheme != st.session_state.colour_scheme:
        st.session_state.colour_scheme = colour_scheme
        st.rerun()
    
    st.divider()
    
    # Font settings
    new_font = st.selectbox(
        "✍️ Font Style",
        FONT_OPTIONS,
        index=FONT_OPTIONS.index(st.session_state.font_style) if st.session_state.font_style in FONT_OPTIONS else 0
    )
    if new_font != st.session_state.font_style:
        st.session_state.font_style = new_font
        st.rerun()
    
    new_size = st.slider(
        "🔤 Text Size",
        MIN_FONT_SIZE, MAX_FONT_SIZE,
        st.session_state.text_size
    )
    if new_size != st.session_state.text_size:
        st.session_state.text_size = new_size
        st.rerun()
    
    # Line spacing
    spacing_options = {"Tight (1.5)": 1.5, "Normal (1.8)": 1.8, "Loose (2.0)": 2.0}
    current_spacing = next((k for k, v in spacing_options.items() if v == st.session_state.line_spacing), "Normal (1.8)")
    new_spacing = st.selectbox("📏 Line Spacing", list(spacing_options.keys()), index=list(spacing_options.keys()).index(current_spacing))
    st.session_state.line_spacing = spacing_options[new_spacing]
    
    st.divider()
    
    # Reading level
    reading_level = st.selectbox("📖 Reading Level", list(READING_LEVELS.keys()))
    
    # Features
    st.session_state.show_images = st.checkbox("🖼️ Show Images", value=st.session_state.show_images)
    
    fun_mode = st.checkbox("✨ Fun Mode (animations)", value=st.session_state.fun_mode)
    if fun_mode != st.session_state.fun_mode:
        st.session_state.fun_mode = fun_mode
        st.rerun()
    
    st.divider()
    
    # Save deck button (only if flashcards exist)
    if st.session_state.flashcard_generated and st.session_state.flashcards:
        if st.button("💾 Save Current Deck", use_container_width=True):
            save_deck_dialog()
    
    st.caption("💡 All settings apply immediately")

# Apply styles
apply_styles(
    st.session_state.font_style,
    st.session_state.text_size,
    st.session_state.colour_scheme,
    mode=st.session_state.color_mode,
    fun_mode=st.session_state.fun_mode,
    line_spacing=st.session_state.line_spacing
)

# --- Header ---
render_header(
    APP_TITLE,
    APP_SUBTITLE,
    st.session_state.text_size,
    st.session_state.colour_scheme,
    fun_mode=st.session_state.fun_mode
)

# --- Main Content ---
st.markdown("## 📝 Your Text")

input_type = st.radio("Input Type", ["✏️ Paste Text", "📁 Upload File"], horizontal=True)

if input_type == "✏️ Paste Text":
    user_text = st.text_area(
        "Type or paste your text...",
        height=150,
        placeholder="Paste any text here – news article, Wikipedia page, or your own notes...",
        label_visibility="collapsed"
    )
else:
    uploaded_file = st.file_uploader("Upload a text file (TXT, PDF, or DOCX)", type=["txt", "pdf", "docx"], label_visibility="collapsed")
    if uploaded_file:
        user_text = extract_text_from_file(uploaded_file)
        st.success(f"✅ Loaded {uploaded_file.name}")
    else:
        user_text = ""

# Character limit warning
if user_text and len(user_text) > MAX_CHARS:
    st.info(f"ℹ️ Using first {MAX_CHARS:,} characters (text is quite long)")
    user_text = user_text[:MAX_CHARS]

word_count = len(user_text.split()) if user_text else 0
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.caption(f"📝 {word_count} words • ⚠️ Text sent to AI for processing")
    
    if st.button("✨ Generate Flashcards ✨", use_container_width=True, type="primary"):
        if not user_text.strip():
            st.warning("⚠️ Please enter or upload some text first!")
        elif word_count < 15:
            st.warning("⚠️ Please add more text (at least 15 words) for better flashcards")
        else:
            level_code = READING_LEVELS[reading_level]
            st.session_state.card_images = {}
            st.session_state.card_flipped = {}
            st.session_state.current_card_idx = 0
            
            with st.spinner(f"🤖 AI is creating {reading_level} flashcards..."):
                new_cards = generate_flashcards_from_llm(user_text, reading_level=level_code)
                if new_cards:
                    st.session_state.flashcards = new_cards
                    st.session_state.flashcard_generated = True
                    
                    # Get images for cards
                    if st.session_state.show_images:
                        with st.spinner("🖼️ Finding images for each card..."):
                            from concurrent.futures import ThreadPoolExecutor
                            search_terms = [(i, c.get('image_search', c['title'])) for i, c in enumerate(new_cards)]
                            with ThreadPoolExecutor(max_workers=5) as pool:
                                results = list(pool.map(lambda item: (item[0], get_best_image(item[1])), search_terms))
                            for idx, url in results:
                                st.session_state.card_images[idx] = url
                    
                    st.success(f"✅ Created {len(new_cards)} flashcards!")
                    st.rerun()

# Show placeholder or flashcards
if not st.session_state.flashcard_generated:
    st.markdown("""
    <div style='text-align: center; padding: 60px 20px; opacity: 0.7;'>
        <div style='font-size: 64px; margin-bottom: 20px;'>📖✨</div>
        <h3>Ready to create some flashcards?</h3>
        <p>Paste text above and click "Generate Flashcards"</p>
    </div>
    """, unsafe_allow_html=True)
else:
    flashcards = st.session_state.flashcards
    total_cards = len(flashcards)
    idx = st.session_state.current_card_idx
    
    # Progress indicator
    flipped_count = sum(1 for i in range(total_cards) if st.session_state.card_flipped.get(i, False))
    progress = flipped_count / total_cards
    
    st.markdown(f"""
    <div style='margin: 20px 0;'>
        <div style='background: #e0e0e0; border-radius: 10px; height: 8px;'>
            <div style='background: linear-gradient(90deg, #4CAF50, #8BC34A); width: {progress*100}%; height: 8px; border-radius: 10px;'></div>
        </div>
        <p style='text-align: center; margin-top: 8px;'>📚 Studied: {flipped_count}/{total_cards} cards</p>
    </div>
    """, unsafe_allow_html=True)
    
    if flipped_count == total_cards:
        st.balloons()
        st.success("🎉 Amazing! You've studied all the cards! 🎉")
    
    # Get current card
    card = flashcards[idx]
    is_flipped = st.session_state.card_flipped.get(idx, False)
    colors = get_card_colors(st.session_state.colour_scheme, st.session_state.color_mode)
    
    # Card display
    st.markdown(f"<h3 style='text-align: center;'>Card {idx + 1} of {total_cards}</h3>", unsafe_allow_html=True)
    
    # Card container
    card_bg = colors.get("card_bg", "#FFFFFF")
    accent = colors["accent"]
    text_color = colors["text"]
    
    if is_flipped:
        # Back of card (facts)
        facts_html = "".join([
            f"""
            <div style='display: flex; align-items: flex-start; gap: 15px; margin: 15px 0; padding: 10px; background: rgba(0,0,0,0.02); border-radius: 12px;'>
                <div style='font-size: 32px;'>{fact['emoji']}</div>
                <div style='flex: 1; font-size: {st.session_state.text_size + 2}px; line-height: {st.session_state.line_spacing};'>{fact['text']}</div>
            </div>
            """ for fact in card['facts']
        ])
        
        # Image if available
        img_html = ""
        if st.session_state.show_images and idx in st.session_state.card_images and st.session_state.card_images[idx]:
            img_html = f"""
            <div style='text-align: center; margin-bottom: 20px;'>
                <img src='{st.session_state.card_images[idx]}' style='max-width: 100%; max-height: 250px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);'>
            </div>
            """
        
        card_html = f"""
        <div style='
            background: {card_bg};
            border-radius: 24px;
            padding: 30px;
            margin: 20px auto;
            max-width: 700px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border-left: 8px solid {accent};
        '>
            {img_html}
            <div style='text-align: center; margin-bottom: 20px;'>
                <span style='background: {accent}; color: white; padding: 5px 15px; border-radius: 20px; font-size: 14px;'>KEY FACTS</span>
            </div>
            {facts_html}
        </div>
        """
    else:
        # Front of card (title)
        img_html = ""
        if st.session_state.show_images and idx in st.session_state.card_images and st.session_state.card_images[idx]:
            img_html = f"""
            <div style='text-align: center; margin-bottom: 20px;'>
                <img src='{st.session_state.card_images[idx]}' style='max-width: 100%; max-height: 200px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);'>
            </div>
            """
        
        card_html = f"""
        <div style='
            background: {card_bg};
            border-radius: 24px;
            padding: 50px 30px;
            margin: 20px auto;
            max-width: 700px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border-top: 8px solid {accent};
        '>
            <div style='font-size: 80px; margin-bottom: 20px;'>{card['emoji']}</div>
            {img_html}
            <div style='font-size: 32px; font-weight: bold; color: {text_color}; margin: 20px 0;'>
                {card['title']}
            </div>
            <div style='font-size: 14px; color: {accent}; margin-top: 20px;'>Click to reveal facts →</div>
        </div>
        """
    
    st.markdown(card_html, unsafe_allow_html=True)
    
    # Buttons
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button("◀ Previous", disabled=(idx == 0), use_container_width=True):
            st.session_state.current_card_idx = max(0, idx - 1)
            st.rerun()
    
    with col2:
        flip_text = "📖 Show Facts" if not is_flipped else "🔙 Show Topic"
        if st.button(flip_text, use_container_width=True, type="primary"):
            st.session_state.card_flipped[idx] = not is_flipped
            st.rerun()
    
    with col3:
        st.markdown(f"<p style='text-align: center; margin-top: 8px;'>{idx + 1} / {total_cards}</p>", unsafe_allow_html=True)
    
    with col4:
        if st.button("Next ▶", disabled=(idx == total_cards - 1), use_container_width=True):
            st.session_state.current_card_idx = min(total_cards - 1, idx + 1)
            st.rerun()
    
    with col5:
        if st.button("🔄 Reset Progress", use_container_width=True):
            st.session_state.card_flipped = {}
            st.rerun()
    
    st.divider()
    
    # Download options
    st.markdown("### 📥 Download")
    col_dl1, col_dl2, col_dl3 = st.columns(3)
    
    with col_dl1:
        # Generate PNG for current card
        img_url = st.session_state.card_images.get(idx) if st.session_state.show_images else None
        img_bytes = fetch_image_bytes(img_url) if img_url else None
        png_bytes = render_card_to_png(
            card=card,
            colors=colors,
            idx=idx,
            total=total_cards,
            wiki_image_bytes=img_bytes,
            page_bg_hex=COLOR_SCHEMES[st.session_state.color_mode][st.session_state.colour_scheme]["bg"]
        )
        st.download_button(
            label="📸 Download This Card (PNG)",
            data=png_bytes,
            file_name=f"flashcard_{idx+1}_{card['title'][:30].replace(' ', '_')}.png",
            mime="image/png",
            use_container_width=True
        )
    
    with col_dl2:
        # Text export
        text_export = "\n\n".join([
            f"TOPIC: {c['title']}\n" + "\n".join([f"  {f['emoji']} {f['text']}" for f in c['facts']])
            for c in flashcards
        ])
        st.download_button(
            label="📝 Download All (Text)",
            data=text_export,
            file_name="flashcards.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col_dl3:
        if st.button("💾 Save Deck for Later", use_container_width=True):
            save_deck_dialog()

# Feedback section
st.divider()
col_fb1, col_fb2, col_fb3 = st.columns([1, 2, 1])
with col_fb2:
    st.markdown(f"""
    <div style='text-align: center; padding: 20px; background: rgba(0,0,0,0.03); border-radius: 16px;'>
        <p>💬 Help improve this app!</p>
        <a href='{FEEDBACK_URL}' target='_blank'>
            <button style='background: {COLOR_SCHEMES[st.session_state.color_mode][st.session_state.colour_scheme]["accent"]}; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer;'>📝 Give Feedback</button>
        </a>
    </div>
    """, unsafe_allow_html=True)
