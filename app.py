# app.py - SIMPLE WORKING VERSION
# Copy this entire code into app.py

import streamlit as st
import os
import re
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ==================== SIMPLE CONFIG ====================

APP_TITLE = "✨ Flashcard Magic ✨"

READING_LEVELS = {
    "Easy (Ages 4-11)": "simple",
    "Medium (Ages 11-18)": "intermediate",
    "Advanced (Ages 18+)": "complex"
}

FONT_OPTIONS = ["Poppins", "Verdana", "Arial", "Comic Sans MS"]

# Simple color schemes that work
COLOR_SCHEMES = {
    "Blue": {"bg": "#E8F1F5", "text": "#1C3A42", "accent": "#3A7CA5"},
    "Green": {"bg": "#E8F5E9", "text": "#1B5E20", "accent": "#43A047"},
    "Purple": {"bg": "#F3E5F5", "text": "#4A148C", "accent": "#AB47BC"},
    "Gray": {"bg": "#F5F5F5", "text": "#424242", "accent": "#757575"},
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

# Apply styles
st.markdown(f"""
<style>
* {{
    font-family: '{st.session_state.font_style}', sans-serif !important;
}}
[data-testid="stAppViewContainer"] {{
    background-color: {colors['bg']} !important;
}}
h1, h2, h3 {{
    color: {colors['accent']} !important;
}}
p, li, label {{
    color: {colors['text']} !important;
    font-size: {st.session_state.font_size}px !important;
}}
.stButton button {{
    background-color: {colors['accent']} !important;
    color: white !important;
    border-radius: 10px !important;
}}
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## Settings")
    
    # Color scheme
    st.markdown("### Color")
    for scheme in COLOR_SCHEMES.keys():
        if st.button(scheme, use_container_width=True):
            st.session_state.color_scheme = scheme
            st.rerun()
    
    st.divider()
    
    # Font
    st.markdown("### Font")
    font = st.selectbox("Font", FONT_OPTIONS, index=FONT_OPTIONS.index(st.session_state.font_style))
    if font != st.session_state.font_style:
        st.session_state.font_style = font
        st.rerun()
    
    # Text size
    size = st.slider("Text Size", 12, 40, st.session_state.font_size)
    if size != st.session_state.font_size:
        st.session_state.font_size = size
        st.rerun()
    
    st.divider()
    
    # Reading level
    reading_level = st.selectbox("Reading Level", list(READING_LEVELS.keys()))

# Main content
st.markdown(f"<h1 style='text-align: center;'>{APP_TITLE}</h1>", unsafe_allow_html=True)

# Text input
user_text = st.text_area("Paste your text here:", height=150)

# Generate button
if st.button("Generate Flashcards", type="primary", use_container_width=True):
    if len(user_text) < 50:
        st.warning("Please enter at least 50 characters")
    else:
        with st.spinner("Creating flashcards..."):
            cards = generate_flashcards(user_text, READING_LEVELS[reading_level])
            if cards:
                st.session_state.flashcards = cards
                st.session_state.generated = True
                st.session_state.card_flipped = {}
                st.session_state.current_idx = 0
                st.rerun()

# Show flashcards
if st.session_state.generated and st.session_state.flashcards:
    cards = st.session_state.flashcards
    idx = st.session_state.current_idx
    card = cards[idx]
    is_flipped = st.session_state.card_flipped.get(idx, False)
    
    # Progress
    flipped_count = sum(st.session_state.card_flipped.get(i, False) for i in range(len(cards)))
    st.progress(flipped_count / len(cards))
    
    # Card
    if not is_flipped:
        st.markdown(f"""
        <div style='background: white; border-radius: 20px; padding: 60px; text-align: center; border-left: 10px solid {colors['accent']};'>
            <div style='font-size: 80px;'>{card['emoji']}</div>
            <h2 style='margin-top: 20px;'>{card['title']}</h2>
            <p style='margin-top: 30px; color: {colors['accent']};'>Click "Reveal Facts" below</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        facts_html = "".join([f"<p>📌 {f['text']}</p>" for f in card['facts']])
        st.markdown(f"""
        <div style='background: white; border-radius: 20px; padding: 40px; border-left: 10px solid {colors['accent']};'>
            <h3 style='text-align: center;'>📖 Key Facts</h3>
            {facts_html}
        </div>
        """, unsafe_allow_html=True)
    
    # Buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("◀ Previous", disabled=(idx == 0)):
            st.session_state.current_idx = max(0, idx - 1)
            st.rerun()
    with col2:
        if st.button("Reveal Facts" if not is_flipped else "Show Topic"):
            st.session_state.card_flipped[idx] = not is_flipped
            st.rerun()
    with col3:
        st.markdown(f"<p style='text-align: center;'>Card {idx + 1} of {len(cards)}</p>", unsafe_allow_html=True)
    with col4:
        if st.button("Next ▶", disabled=(idx == len(cards) - 1)):
            st.session_state.current_idx = min(len(cards) - 1, idx + 1)
            st.rerun()
    
    # Reset
    if st.button("Reset All Cards"):
        st.session_state.card_flipped = {}
        st.rerun()

st.divider()
st.caption("Made with DeepSeek API")
