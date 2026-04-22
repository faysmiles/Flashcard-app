import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

import streamlit as st

# ==================== AUTO-CREATE THEME CONFIG ====================
def create_streamlit_config():
    """Create .streamlit/config.toml automatically at startup"""
    config_dir = os.path.expanduser("~/.streamlit")
    config_file = os.path.join(config_dir, "config.toml")
    
    # Create directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    
    # Write config file
    theme_config = """[theme]
primaryColor = "#D4A017"
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
"""
    
    with open(config_file, "w") as f:
        f.write(theme_config)

# Create config on startup
create_streamlit_config()

# ==================== IMPORTS FROM config.py ====================
from config import (
    APP_TITLE, APP_SUBTITLE, READING_LEVELS, FONT_OPTIONS,
    MIN_FONT_SIZE, MAX_FONT_SIZE, DEFAULT_FONT_SIZE
)
from utils import apply_styles, extract_text_from_file, generate_flashcards_from_llm, get_card_colors

# Page config
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if "flashcard_generated" not in st.session_state:
    st.session_state.flashcard_generated = False
if "summary_data" not in st.session_state:
    st.session_state.summary_data = None
if "final_input_text" not in st.session_state:
    st.session_state.final_input_text = ""
if "font_style" not in st.session_state:
    st.session_state.font_style = "Verdana"
if "text_size" not in st.session_state:
    st.session_state.text_size = DEFAULT_FONT_SIZE
if "colour_scheme" not in st.session_state:
    st.session_state.colour_scheme = "Cream (Dyslexia Friendly)"

# APPLY STYLES FIRST - before any other content
apply_styles(st.session_state.font_style, st.session_state.text_size, st.session_state.colour_scheme)

# ==================== MAIN UI ====================

# Define feedback URL at the top so it's accessible
FEEDBACK_URL = "https://docs.google.com/forms/d/e/1FAIpQLSftcBkHjYju-nNZ0uENPLc1CNSLTrEV3WBR0PenubeZALjypw/viewform"

# ==================== HEADER: TITLE (LEFT) + SURVEY LINK (RIGHT) ====================
header_left, header_right = st.columns([2, 1], gap="medium")

with header_left:
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #D4A017 0%, #E8B923 50%, #DAA520 100%); padding: 28px 26px; border-radius: 12px; box-shadow: 0 4px 16px rgba(218, 165, 32, 0.25); height: 100%; box-sizing: border-box;'>
        <h1 style='font-size: 2em; font-weight: 800; color: #FFFFFF; margin: 0; letter-spacing: -0.5px; line-height: 1.1; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);'>💡 {APP_TITLE}</h1>
        <p style='font-size: 0.95em; color: rgba(255, 255, 255, 0.95); margin: 10px 0 0 0; font-weight: 400; line-height: 1.5;'>{APP_SUBTITLE}</p>
    </div>
    """, unsafe_allow_html=True)

with header_right:
    st.markdown(
        f"""
        <div style='text-align:center; padding:20px 16px; background:rgba(255, 107, 107, 0.08); border:2px solid rgba(255, 107, 107, 0.2); border-radius:12px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center;'>
            <p style='margin:0 0 8px 0; font-size:0.95em; font-weight:700; color:#2C2416;'>💬 Help improve this app!</p>
            <p style='margin:0 0 12px 0; font-size:0.8em; color:#5C5246;'>Your feedback supports our research</p>
            <a href='{FEEDBACK_URL}' target='_blank' style='display:inline-block; padding:10px 20px; background:#FF6B6B; color:white; text-decoration:none; border-radius:8px; font-weight:700; font-size:0.9em; box-shadow:0 4px 12px rgba(255, 107, 107, 0.25);'>📝 Take Survey</a>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<div style='margin-bottom: 28px;'></div>", unsafe_allow_html=True)

# Create two columns: settings on left, content on right
settings_col, content_col = st.columns([0.95, 3.5], gap="medium")

# ==================== SETTINGS COLUMN ====================
with settings_col:
    st.markdown("""
    <style>
    .settings-container {{
        background: rgba(255, 255, 255, 0.8);
        padding: 24px;
        border-radius: 12px;
        border-left: 4px solid #D4A017;
    }}
    
    .settings-title {{
        font-size: 1.2em;
        font-weight: 700;
        color: #2C2416;
        margin: 0 0 20px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    
    .setting-group {{
        margin-bottom: 22px;
    }}
    
    .setting-label {{
        font-size: 0.95em;
        font-weight: 600;
        color: #3E2723;
        margin-bottom: 8px;
        display: block;
    }}
    </style>
    
    <div class="settings-container">
        <div class="settings-title">⚙️ Settings</div>
    """, unsafe_allow_html=True)
    
    # Reading level
    st.markdown('<div class="setting-group">', unsafe_allow_html=True)
    st.markdown('<label class="setting-label">Reading Level</label>', unsafe_allow_html=True)
    reading_level = st.selectbox(
        "Reading Level",
        list(READING_LEVELS.keys()),
        key="reading_level_select",
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Font selection
    st.markdown('<div class="setting-group">', unsafe_allow_html=True)
    st.markdown('<label class="setting-label">Font Style</label>', unsafe_allow_html=True)
    new_font = st.selectbox(
        "Font",
        FONT_OPTIONS,
        index=FONT_OPTIONS.index(st.session_state.font_style),
        key="font_selectbox",
        label_visibility="collapsed"
    )
    if new_font != st.session_state.font_style:
        st.session_state.font_style = new_font
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Text size
    st.markdown('<div class="setting-group">', unsafe_allow_html=True)
    st.markdown('<label class="setting-label">Text Size</label>', unsafe_allow_html=True)
    new_size = st.slider(
        "Text Size (px)",
        MIN_FONT_SIZE, MAX_FONT_SIZE,
        st.session_state.text_size,
        key="text_size_slider",
        label_visibility="collapsed"
    )
    if new_size != st.session_state.text_size:
        st.session_state.text_size = new_size
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Color scheme
    st.markdown('<div class="setting-group">', unsafe_allow_html=True)
    st.markdown('<label class="setting-label">Color Scheme</label>', unsafe_allow_html=True)
    new_colour = st.selectbox(
        "Colours",
        [
            "Cream (Dyslexia Friendly)",
            "Soft Blue",
            "Light Grey",
            "Pale Lavender",
            "Pale Mint"
        ],
        index=[
            "Cream (Dyslexia Friendly)",
            "Soft Blue",
            "Light Grey",
            "Pale Lavender",
            "Pale Mint"
        ].index(st.session_state.colour_scheme),
        key="colour_selectbox",
        label_visibility="collapsed"
    )
    if new_colour != st.session_state.colour_scheme:
        st.session_state.colour_scheme = new_colour
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Make pictures checkbox
    st.markdown('<div class="setting-group">', unsafe_allow_html=True)
    make_pictures = st.checkbox(
        "Show Images",
        value=True,
        key="make_pictures_check",
        help="Show relevant images from Wikipedia on flipped cards"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    
    st.markdown('</div>', unsafe_allow_html=True)

# ==================== CONTENT COLUMN ====================
with content_col:
    st.markdown("""
    <style>
    .content-section {{
        background: rgba(255, 255, 255, 0.5);
        padding: 28px;
        border-radius: 12px;
        margin-bottom: 28px;
    }}
    
    .section-title {{
        font-size: 1.15em;
        font-weight: 700;
        color: #2C2416;
        margin-bottom: 16px;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Input section
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📝 Your Text</div>', unsafe_allow_html=True)
    
    input_type = st.radio(
        "Input Type",
        ["Paste Text", "Upload File"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if input_type == "Paste Text":
        user_text = st.text_area(
            "Type, paste or upload text...",
            height=150,
            placeholder="Paste your text here...",
            label_visibility="collapsed"
        )
    else:
        uploaded_file = st.file_uploader(
            "Upload a text file (TXT, PDF, or DOCX)",
            type=["txt", "pdf", "docx"],
            label_visibility="collapsed"
        )
        if uploaded_file:
            user_text = extract_text_from_file(uploaded_file)
            st.success(f"✅ Loaded {uploaded_file.name}")
        else:
            user_text = ""
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Make Flashcard button
    st.markdown("""
    <style>
    .button-container {{
        display: flex;
        justify-content: center;
        margin: 28px 0;
    }}
    
    .make-flashcard-btn {{
        background: linear-gradient(135deg, #D4A017 0%, #C9901F 100%);
        color: white;
        border: none;
        padding: 16px 48px;
        font-size: 1.05em;
        font-weight: 700;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(212, 160, 23, 0.25);
    }}
    
    .make-flashcard-btn:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(212, 160, 23, 0.35);
    }}
    </style>
    """, unsafe_allow_html=True)
    
    button_col1, button_col2, button_col3 = st.columns([1, 1.2, 1])
    with button_col2:
        if st.button("✨ Make Flashcard", use_container_width=True, key="make_flashcard_btn"):
            if user_text.strip():
                # Use LLM to extract flashcards directly
                with st.spinner("🤖 AI is extracting flashcards..."):
                    from utils import generate_flashcards_from_llm
                    flashcards = generate_flashcards_from_llm(user_text)
                    if flashcards:
                        st.session_state.flashcards_direct = flashcards
                        st.session_state.final_input_text = user_text
                        st.session_state.flashcard_generated = True
            else:
                st.warning("⚠️ Please enter or upload some text first!")
    
    # Display flashcards if generated
    if st.session_state.flashcard_generated:
        # Get flashcards from AI extraction
        if "flashcards_direct" in st.session_state and st.session_state.flashcards_direct:
            flashcards = st.session_state.flashcards_direct
        else:
            flashcards = []
        
        if flashcards:
            # Initialize flip state for cards if not exists
            if "card_flipped" not in st.session_state:
                st.session_state.card_flipped = {}
            
            # Ensure all card indices exist in the flip state
            for i in range(len(flashcards)):
                if i not in st.session_state.card_flipped:
                    st.session_state.card_flipped[i] = False
        
        # Get dyslexia-friendly colors for the selected scheme
        card_colors = get_card_colors(st.session_state.colour_scheme)
        
        # Flashcards section header
        st.markdown(f"""
        <style>
        .flashcards-header {{
            margin-top: 40px;
            margin-bottom: 28px;
            padding-bottom: 16px;
            border-bottom: 3px solid #D4A017;
        }}
        
        .flashcards-title {{
            font-size: 1.5em;
            font-weight: 800;
            color: #2C2416;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .card-count {{
            font-size: 0.9em;
            color: #666666;
            font-weight: 500;
            margin-left: auto;
        }}
        </style>
        
        <div class="flashcards-header">
            <div class="flashcards-title">
                📚 Your Flashcards
                <span class="card-count">({len(flashcards)} cards)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize image cache for cards
        if "card_images" not in st.session_state:
            st.session_state.card_images = {}
        
        # Progress counter only (buttons removed for simplicity)
        flipped_count = sum(1 for i in range(len(flashcards)) if st.session_state.card_flipped.get(i, False))
        st.markdown(
            f"<div style='padding:10px; text-align:center; background:rgba(212, 160, 23, 0.1); border-radius:8px; font-weight:700; color:#D4A017; font-size:0.9em; margin:10px 0 20px 0;'>👀 Studied: {flipped_count}/{len(flashcards)}</div>",
            unsafe_allow_html=True
        )
        
        # Decorative emojis for visual stimulation
        DECORATION_EMOJIS = ['✨', '⭐', '💫', '🌟', '🎯', '📚', '💡', '🎨']
        
        # Display each flashcard - SIMPLE AND CLEAN
        for idx, card in enumerate(flashcards):
            is_flipped = st.session_state.card_flipped.get(idx, False)
            emoji = card.get('emoji', '💡')
            
            # Get 4 decorative emojis
            deco = [
                DECORATION_EMOJIS[idx % len(DECORATION_EMOJIS)],
                DECORATION_EMOJIS[(idx + 2) % len(DECORATION_EMOJIS)],
                DECORATION_EMOJIS[(idx + 4) % len(DECORATION_EMOJIS)],
                DECORATION_EMOJIS[(idx + 6) % len(DECORATION_EMOJIS)]
            ]
            
            button_key = f"flip_{idx}"
            
            # Get colors
            bg_color = card_colors['flipped_bg'] if is_flipped else card_colors['question_bg']
            text_color = card_colors['text']
            label_color = card_colors['label']
            
            # Card counter with gold accent
            st.markdown(f"<p style='text-align:center; color:#D4A017; font-weight:800; letter-spacing:3px; margin:32px 0 10px 0; font-size:0.9em;'>✨ CARD {idx + 1} OF {len(flashcards)} ✨</p>", unsafe_allow_html=True)
            
            # Fetch image (fast Wikipedia search - no API key needed!)
            if is_flipped and make_pictures and idx not in st.session_state.card_images:
                with st.spinner(f"🖼️ Finding picture for card {idx + 1}..."):
                    from utils import search_wikipedia_image
                    image_url = search_wikipedia_image(card['title'])
                    if image_url:
                        st.session_state.card_images[idx] = image_url
                    else:
                        st.session_state.card_images[idx] = None
            
            # ==================== THE FLASHCARD - ONE BIG STYLED HTML BLOCK ====================
            if is_flipped:
                # BACK - Facts (+ optional image)
                has_image = (make_pictures 
                             and idx in st.session_state.card_images 
                             and st.session_state.card_images[idx] is not None)
                
                facts_list_html = "".join([
                    f"<li style='color:{text_color}; font-family:{st.session_state.font_style}, sans-serif; font-size:{st.session_state.text_size}px; line-height:1.9; margin:10px 0; padding-left:8px;'>{fact}</li>"
                    for fact in card['facts']
                ])
                
                if has_image:
                    image_url = st.session_state.card_images[idx]
                    card_html = (
                        f"<div style='background:linear-gradient(135deg, {bg_color} 0%, #FFFFFF 100%); "
                        f"border-left:8px solid #D4A017; border-radius:20px; padding:36px 32px; margin:8px 0 20px 0; "
                        f"box-shadow: 0 12px 32px rgba(212, 160, 23, 0.18), 0 4px 12px rgba(0,0,0,0.08); "
                        f"position:relative; overflow:hidden;'>"
                        f"<div style='position:absolute; top:14px; right:18px; font-size:26px; opacity:0.35;'>{deco[0]} {deco[1]}</div>"
                        f"<p style='text-align:center; color:#D4A017; font-weight:800; letter-spacing:3px; font-size:0.9em; margin:0 0 20px 0;'>📋 KEY FACTS</p>"
                        f"<div style='display:flex; gap:24px; align-items:center; flex-wrap:wrap;'>"
                        f"<div style='flex:1.4; min-width:280px;'>"
                        f"<ul style='list-style:'✦  '; padding-left:20px; margin:0;'>{facts_list_html}</ul>"
                        f"</div>"
                        f"<div style='flex:1; min-width:220px; text-align:center;'>"
                        f"<img src='{image_url}' style='width:100%; max-width:260px; border-radius:12px; box-shadow:0 6px 16px rgba(0,0,0,0.15);' />"
                        f"</div>"
                        f"</div>"
                        f"<div style='position:absolute; bottom:14px; left:18px; font-size:24px; opacity:0.35;'>{deco[2]} {deco[3]}</div>"
                        f"</div>"
                    )
                else:
                    card_html = (
                        f"<div style='background:linear-gradient(135deg, {bg_color} 0%, #FFFFFF 100%); "
                        f"border-left:8px solid #D4A017; border-radius:20px; padding:40px 36px; margin:8px 0 20px 0; "
                        f"box-shadow: 0 12px 32px rgba(212, 160, 23, 0.18), 0 4px 12px rgba(0,0,0,0.08); "
                        f"position:relative; overflow:hidden; min-height:260px;'>"
                        f"<div style='position:absolute; top:14px; right:18px; font-size:26px; opacity:0.35;'>{deco[0]} {deco[1]}</div>"
                        f"<p style='text-align:center; color:#D4A017; font-weight:800; letter-spacing:3px; font-size:0.9em; margin:0 0 24px 0;'>📋 KEY FACTS</p>"
                        f"<ul style='list-style:none; padding-left:8px; margin:0;'>{facts_list_html}</ul>"
                        f"<div style='position:absolute; bottom:14px; left:18px; font-size:24px; opacity:0.35;'>{deco[2]} {deco[3]}</div>"
                        f"</div>"
                    )
                st.markdown(card_html, unsafe_allow_html=True)
            else:
                # FRONT - Big emoji and title (striking, prominent)
                front_html = (
                    f"<div style='background:linear-gradient(135deg, {bg_color} 0%, #FFFFFF 100%); "
                    f"border-left:8px solid #D4A017; border-radius:20px; padding:56px 40px; margin:8px 0 20px 0; "
                    f"box-shadow: 0 12px 32px rgba(212, 160, 23, 0.18), 0 4px 12px rgba(0,0,0,0.08); "
                    f"text-align:center; position:relative; overflow:hidden; min-height:280px;'>"
                    f"<div style='position:absolute; top:18px; left:22px; font-size:32px; opacity:0.35;'>{deco[0]}</div>"
                    f"<div style='position:absolute; top:18px; right:22px; font-size:32px; opacity:0.35;'>{deco[1]}</div>"
                    f"<div style='font-size:110px; line-height:1; margin-bottom:20px;'>{emoji}</div>"
                    f"<p style='color:#D4A017; font-weight:800; letter-spacing:4px; font-size:0.9em; margin:0 0 16px 0;'>⭐ TOPIC ⭐</p>"
                    f"<h2 style='color:{text_color}; font-family:{st.session_state.font_style}, sans-serif; font-size:{max(st.session_state.text_size + 12, 28)}px; margin:0; font-weight:800; padding:0 20px;'>{card['title']}</h2>"
                    f"<div style='position:absolute; bottom:18px; left:22px; font-size:32px; opacity:0.35;'>{deco[2]}</div>"
                    f"<div style='position:absolute; bottom:18px; right:22px; font-size:32px; opacity:0.35;'>{deco[3]}</div>"
                    f"</div>"
                )
                st.markdown(front_html, unsafe_allow_html=True)
            
            # Flip button with better text
            button_col1, button_col2, button_col3 = st.columns([1, 1, 1])
            with button_col2:
                flip_text = "🔄 Show Topic" if is_flipped else "🔄 Reveal Facts"
                if st.button(flip_text, key=button_key, use_container_width=True):
                    st.session_state.card_flipped[idx] = not st.session_state.card_flipped.get(idx, False)
                    st.rerun()
        
        # Study tools section
        st.markdown("""
        <style>
        .study-tools {{
            margin-top: 40px;
            padding-top: 28px;
            border-top: 2px solid rgba(212, 160, 23, 0.2);
        }}
        
        .tools-title {{
            font-size: 1.15em;
            font-weight: 700;
            color: #2C2416;
            margin-bottom: 16px;
        }}
        </style>
        
        <div class="study-tools">
            <div class="tools-title">📥 Study Tools</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Download button
        download_col1, download_col2, download_col3 = st.columns([1, 1.2, 1])
        with download_col2:
            st.download_button(
                label="📥 Download Study Cards",
                data="\n\n".join([f"TOPIC: {card['title']}\nFACTS:\n" + "\n".join([f"  • {fact}" for fact in card['facts']]) for card in flashcards]),
                file_name="study_cards.txt",
                mime="text/plain",
                use_container_width=True
            )