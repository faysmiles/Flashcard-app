# app.py - PREMIUM SHINY BUTTONS WITH GLOW EFFECTS
# Copy this entire code into app.py

import streamlit as st
import os
import re
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ==================== CONFIG ====================

APP_TITLE = "Flashcard Magic"

READING_LEVELS = {
    "Easy (Ages 4-11)": "simple",
    "Medium (Ages 11-18)": "intermediate",
    "Advanced (Ages 18+)": "complex"
}

FONT_OPTIONS = ["Poppins", "Verdana", "Arial", "Comic Sans MS"]

# Color schemes with shiny metallic gradients
COLOR_SCHEMES = {
    "Blue": {"bg": "#E8F1F5", "text": "#1C3A42", "accent": "#3A7CA5", 
             "gradient": "linear-gradient(145deg, #4A90C4, #2C5F7E, #3A7CA5)",
             "shadow": "#1E4057", "glow": "#6BB5E0"},
    "Green": {"bg": "#E8F5E9", "text": "#1B5E20", "accent": "#43A047",
             "gradient": "linear-gradient(145deg, #5CB860, #2E7D32, #43A047)",
             "shadow": "#1B5E20", "glow": "#7BCF80"},
    "Purple": {"bg": "#F3E5F5", "text": "#4A148C", "accent": "#AB47BC",
             "gradient": "linear-gradient(145deg, #C158D0, #8E24AA, #AB47BC)",
             "shadow": "#6A1B9A", "glow": "#D47BE0"},
    "Gray": {"bg": "#F5F5F5", "text": "#424242", "accent": "#757575",
             "gradient": "linear-gradient(145deg, #8A8A8A, #616161, #757575)",
             "shadow": "#424242", "glow": "#A0A0A0"},
}

def get_emoji(text):
    emojis = {"lion": "🦁", "elephant": "🐘", "bird": "🦅", "heart": "❤️", "star": "⭐", "book": "📖"}
    for key, emoji in emojis.items():
        if key in text.lower():
            return emoji
    return "✨"

def generate_flashcards(text, reading_level):
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["DEEPSEEK_API_KEY"]
        except:
            return None
    
    prompt = f"""Create 3 flashcards from this text. Reading level: {reading_level}
Return ONLY JSON: {{"flashcards": [{{"title": "short title", "facts": ["fact1", "fact2"]}}]}}

Text: {text[:5000]}"""

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        
        result = json.loads(response.choices[0].message.content)
        cards = result.get("flashcards", [])
        
        flashcards = []
        for card in cards:
            flashcards.append({
                "title": card["title"],
                "facts": [{"emoji": get_emoji(fact), "text": fact} for fact in card.get("facts", [])],
                "emoji": get_emoji(card["title"])
            })
        return flashcards
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# ==================== MAIN APP ====================

st.set_page_config(page_title="Flashcard Magic", page_icon="✨", layout="wide")

# Session state
if "flashcards" not in st.session_state:
    st.session_state.flashcards = None
if "generated" not in st.session_state:
    st.session_state.generated = False
if "card_flipped" not in st.session_state:
    st.session_state.card_flipped = {}
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0
if "font_size" not in st.session_state:
    st.session_state.font_size = 18
if "font_style" not in st.session_state:
    st.session_state.font_style = "Poppins"
if "color_scheme" not in st.session_state:
    st.session_state.color_scheme = "Blue"

# Get current colors
colors = COLOR_SCHEMES[st.session_state.color_scheme]

# ========== PREMIUM SHINY BUTTON STYLES ==========
st.markdown(f"""
<style>
/* Global styles */
* {{
    font-family: '{st.session_state.font_style}', sans-serif !important;
}}

[data-testid="stAppViewContainer"] {{
    background-color: {colors['bg']} !important;
}}

h1, h2, h3 {{
    color: {colors['accent']} !important;
}}

p, li, label, .stMarkdown {{
    color: {colors['text']} !important;
    font-size: {st.session_state.font_size}px !important;
}}

/* ===== PREMIUM SHINY BUTTONS ===== */

/* All buttons - metallic shiny effect */
.stButton button {{
    background: {colors['gradient']} !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 10px 20px !important;
    font-weight: bold !important;
    font-size: 15px !important;
    cursor: pointer !important;
    box-shadow: 0 5px 0 {colors['shadow']}, 0 2px 10px rgba(0,0,0,0.2) !important;
    transition: all 0.1s ease !important;
    text-shadow: 0 1px 1px rgba(0,0,0,0.3) !important;
    position: relative !important;
    overflow: hidden !important;
}}

/* Shiny highlight overlay */
.stButton button::before {{
    content: '' !important;
    position: absolute !important;
    top: 0 !important;
    left: -100% !important;
    width: 100% !important;
    height: 100% !important;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent) !important;
    transition: left 0.5s ease !important;
}}

/* Shine effect on hover */
.stButton button:hover::before {{
    left: 100% !important;
}}

/* Glow effect on hover */
.stButton button:hover {{
    filter: brightness(1.08) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 7px 0 {colors['shadow']}, 0 0 15px {colors['glow']} !important;
}}

/* Press effect */
.stButton button:active {{
    transform: translateY(3px) !important;
    box-shadow: 0 2px 0 {colors['shadow']} !important;
}}

/* Disabled buttons */
.stButton button:disabled {{
    opacity: 0.5 !important;
    transform: none !important;
    cursor: not-allowed !important;
}}

/* Primary button - extra shiny and big */
.stButton button[kind="primary"] {{
    background: linear-gradient(145deg, {colors['accent']}, {colors['shadow']}, {colors['accent']}) !important;
    background-size: 200% 200% !important;
    animation: shimmer 3s ease infinite !important;
    box-shadow: 0 8px 0 {colors['shadow']}, 0 4px 15px rgba(0,0,0,0.3) !important;
    font-size: 20px !important;
    padding: 14px 28px !important;
}}

@keyframes shimmer {{
    0% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}

.stButton button[kind="primary"]:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 0 {colors['shadow']}, 0 0 20px {colors['glow']} !important;
}}

.stButton button[kind="primary"]:active {{
    transform: translateY(4px) !important;
    box-shadow: 0 4px 0 {colors['shadow']} !important;
}}

/* Color theme buttons in sidebar - metallic */
[data-testid="stSidebar"] .stButton button {{
    margin: 6px 0 !important;
    font-size: 14px !important;
    text-align: left !important;
    padding: 10px 16px !important;
}}

/* Card flip button - special metallic orange */
div:has(> button:contains("Reveal")) .stButton button,
div:has(> button:contains("Show")) .stButton button {{
    background: linear-gradient(145deg, #FF9800, #E65100, #F57C00) !important;
    box-shadow: 0 5px 0 #BF360C !important;
    animation: shimmer 3s ease infinite !important;
}}

div:has(> button:contains("Reveal")) .stButton button:hover,
div:has(> button:contains("Show")) .stButton button:hover {{
    box-shadow: 0 7px 0 #BF360C, 0 0 15px #FF9800 !important;
}}

/* Navigation buttons */
div:has(> button:contains("Previous")) .stButton button,
div:has(> button:contains("Next")) .stButton button {{
    background: linear-gradient(145deg, #607D8B, #37474F, #455A64) !important;
    box-shadow: 0 5px 0 #263238 !important;
}}

/* Reset button */
div:has(> button:contains("Reset")) .stButton button {{
    background: linear-gradient(145deg, #EF5350, #C62828, #E53935) !important;
    box-shadow: 0 5px 0 #B71C1C !important;
}}

/* ===== CARD STYLES WITH SHADOW AND GLOW ===== */

/* Flashcard container */
div:has(> div:contains("📖 Key Facts")), 
div:has(> div:contains("flashcard")) {{
    animation: slideIn 0.3s ease-out;
    transition: all 0.2s ease !important;
}}

/* Card hover effect - subtle lift and glow */
div[style*="background: white"] {{
    transition: all 0.2s ease !important;
}}

div[style*="background: white"]:hover {{
    transform: translateY(-3px) !important;
    box-shadow: 0 15px 35px rgba(0,0,0,0.2) !important;
}}

@keyframes slideIn {{
    from {{ opacity: 0; transform: translateY(20px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

/* Progress bar with gradient and glow */
[data-testid="stProgress"] > div > div > div > div {{
    background: linear-gradient(90deg, {colors['accent']}, {colors['glow']}) !important;
    box-shadow: 0 0 8px {colors['glow']} !important;
    border-radius: 10px !important;
}}

/* Sidebar elements with subtle hover */
[data-testid="stSidebar"] .stSelectbox:hover,
[data-testid="stSidebar"] .stSlider:hover {{
    opacity: 0.9 !important;
}}

/* Slider thumb glow */
[data-testid="stSlider"] div[role="slider"] {{
    background: {colors['accent']} !important;
    box-shadow: 0 0 8px {colors['glow']} !important;
    transition: all 0.1s ease !important;
}}

[data-testid="stSlider"] div[role="slider"]:hover {{
    transform: scale(1.1) !important;
    box-shadow: 0 0 12px {colors['glow']} !important;
}}

/* Select box hover effect */
[data-testid="stSelectbox"] div[data-baseweb="select"]:hover {{
    border-color: {colors['accent']} !important;
    box-shadow: 0 0 8px {colors['glow']} !important;
}}
</style>
""", unsafe_allow_html=True)

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown(f"## Settings")
    
    # Color theme - clean buttons (no emoji)
    st.markdown("### Color Theme")
    for scheme in COLOR_SCHEMES.keys():
        if st.button(scheme, use_container_width=True):
            st.session_state.color_scheme = scheme
            st.rerun()
    
    st.divider()
    
    # Font selection
    st.markdown("### Font")
    font = st.selectbox("Choose your font", FONT_OPTIONS, index=FONT_OPTIONS.index(st.session_state.font_style))
    if font != st.session_state.font_style:
        st.session_state.font_style = font
        st.rerun()
    
    # Text size slider
    st.markdown("### Text Size")
    size = st.slider("Adjust size", 12, 40, st.session_state.font_size)
    if size != st.session_state.font_size:
        st.session_state.font_size = size
        st.rerun()
    
    st.divider()
    
    # Reading level
    st.markdown("### Reading Level")
    reading_level = st.selectbox("Select level", list(READING_LEVELS.keys()))
    
    st.divider()
    st.caption("✨ Shiny 3D buttons")
    st.caption("💡 Hover over anything with your cursor")

# ========== MAIN CONTENT ==========

# Title
st.markdown(f"""
<div style='text-align: center; padding: 20px;'>
    <h1 style='font-size: 48px; margin: 10px 0;'>{APP_TITLE}</h1>
    <p style='font-size: 18px; opacity: 0.8;'>Turn any text into fun flashcards</p>
</div>
""", unsafe_allow_html=True)

# Text input area
st.markdown("## Your Text")
input_type = st.radio("Input Type", ["Paste Text", "Upload File"], horizontal=True)

user_text = ""
if input_type == "Paste Text":
    user_text = st.text_area("Paste your text here...", height=150, placeholder="Paste any text - article, notes, Wikipedia page...", label_visibility="collapsed")
else:
    uploaded = st.file_uploader("Upload TXT, PDF, or DOCX", type=["txt", "pdf", "docx"], label_visibility="collapsed")
    if uploaded:
        try:
            if uploaded.type == "text/plain":
                user_text = uploaded.read().decode('utf-8')
            else:
                user_text = f"File uploaded: {uploaded.name}"
            st.success(f"Loaded {uploaded.name}")
        except:
            st.error("Could not read file")

word_count = len(user_text.split()) if user_text else 0
st.caption(f"📝 {word_count} words")

# Generate button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("Generate Flashcards", type="primary", use_container_width=True):
        if len(user_text) < 50:
            st.warning("Please enter more text (at least 50 characters)")
        else:
            with st.spinner("Creating your flashcards..."):
                cards = generate_flashcards(user_text, READING_LEVELS[reading_level])
                if cards:
                    st.session_state.flashcards = cards
                    st.session_state.generated = True
                    st.session_state.card_flipped = {}
                    st.session_state.current_idx = 0
                    st.rerun()

# Display flashcards
if st.session_state.generated and st.session_state.flashcards:
    cards = st.session_state.flashcards
    idx = st.session_state.current_idx
    card = cards[idx]
    is_flipped = st.session_state.card_flipped.get(idx, False)
    
    # Progress bar
    flipped_count = sum(st.session_state.card_flipped.get(i, False) for i in range(len(cards)))
    st.progress(flipped_count / len(cards))
    st.caption(f"Progress: {flipped_count}/{len(cards)} cards studied")
    
    if flipped_count == len(cards):
        st.balloons()
        st.success("Congratulations! You've mastered all cards!")
    
    # Flashcard with shadow and hover lift
    if not is_flipped:
        st.markdown(f"""
        <div style='
            background: white; 
            border-radius: 24px; 
            padding: 60px 40px; 
            text-align: center; 
            border-left: 12px solid {colors['accent']};
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            margin: 20px 0;
            transition: all 0.2s ease;
        '>
            <div style='font-size: 80px; margin-bottom: 20px;'>{card['emoji']}</div>
            <h2 style='margin: 20px 0; color: {colors['text']};'>{card['title']}</h2>
            <p style='margin-top: 30px; color: {colors['accent']}; font-size: 14px;'>Click "Reveal Facts" below to learn more</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        facts_html = "".join([f"""
        <div style='
            display: flex; 
            align-items: center; 
            gap: 15px; 
            padding: 15px; 
            margin: 10px 0;
            background: {colors['bg']}; 
            border-radius: 12px;
            transition: all 0.2s ease;
        '>
            <div style='font-size: 32px;'>{f['emoji']}</div>
            <div style='flex: 1; font-size: {st.session_state.font_size}px;'>{f['text']}</div>
        </div>
        """ for f in card['facts']])
        
        st.markdown(f"""
        <div style='
            background: white; 
            border-radius: 24px; 
            padding: 40px; 
            border-left: 12px solid {colors['accent']};
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            margin: 20px 0;
            transition: all 0.2s ease;
        '>
            <h3 style='text-align: center; margin-bottom: 30px; color: {colors['accent']};'>Key Facts</h3>
            {facts_html}
        </div>
        """, unsafe_allow_html=True)
    
    # Navigation buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("Previous", disabled=(idx == 0), use_container_width=True):
            st.session_state.current_idx = max(0, idx - 1)
            st.rerun()
    with col2:
        if st.button("Reveal Facts" if not is_flipped else "Show Topic", use_container_width=True):
            st.session_state.card_flipped[idx] = not is_flipped
            st.rerun()
    with col3:
        st.markdown(f"<p style='text-align: center; margin-top: 10px;'><strong>{idx + 1}</strong> / {len(cards)}</p>", unsafe_allow_html=True)
    with col4:
        if st.button("Next", disabled=(idx == len(cards) - 1), use_container_width=True):
            st.session_state.current_idx = min(len(cards) - 1, idx + 1)
            st.rerun()
    
    # Reset button
    if st.button("Reset All Cards", use_container_width=True):
        st.session_state.card_flipped = {}
        st.rerun()
    
    # Download section
    st.divider()
    st.markdown("### Download")
    text_export = "\n\n".join([f"TOPIC: {c['title']}\n" + "\n".join([f"  {f['emoji']} {f['text']}" for f in c['facts']]) for c in cards])
    st.download_button("Download All Cards (Text)", text_export, "flashcards.txt", use_container_width=True)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; padding: 20px;'>
    <p>Made with DeepSeek API • No data stored • Your privacy is protected</p>
</div>
""", unsafe_allow_html=True)
