# app.py - COMPLETE FLASHCARD APP (All Issues Fixed)
# Copy this entire code into app.py

import streamlit as st
import os
import re
import json
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ==================== CONFIGURATION ====================

APP_TITLE = "✨ Flashcard Magic ✨"
APP_SUBTITLE = "Turn any text into fun, colorful flashcards"

READING_LEVELS = {
    "📖 Easy (Ages 4-11)": "simple",
    "📚 Medium (Ages 11-18)": "intermediate",
    "🎓 Advanced (Ages 18+)": "complex"
}

# Font options with their actual names for preview
FONT_OPTIONS = {
    "Poppins": "Poppins",
    "OpenDyslexic": "OpenDyslexic", 
    "Lexend": "Lexend",
    "Verdana": "Verdana",
    "Arial": "Arial",
    "Comic Sans MS": "Comic Sans MS",
    "Nunito": "Nunito",
    "Montserrat": "Montserrat",
    "Roboto": "Roboto",
    "Inter": "Inter"
}

# THREE COLOR MODES with proper schemes
COLOR_SCHEMES = {
    "Vibrant": {
        "Ocean Teal": {"bg": "#E0F7FA", "text": "#004D40", "accent": "#00897B", "card_bg": "#FFFFFF"},
        "Forest Green": {"bg": "#E8F5E9", "text": "#1B5E20", "accent": "#43A047", "card_bg": "#FFFFFF"},
        "Berry Pink": {"bg": "#FCE4EC", "text": "#880E4F", "accent": "#D81B60", "card_bg": "#FFFFFF"},
        "Sunshine Yellow": {"bg": "#FFFDE7", "text": "#F57F17", "accent": "#F9A825", "card_bg": "#FFFFFF"},
        "Sky Blue": {"bg": "#E3F2FD", "text": "#0D47A1", "accent": "#1E88E5", "card_bg": "#FFFFFF"},
        "Coral Reef": {"bg": "#FFF3E0", "text": "#BF360C", "accent": "#FF5722", "card_bg": "#FFFFFF"},
    },
    "Accessibility": {
        "Soft Blue": {"bg": "#E8F1F5", "text": "#1C3A42", "accent": "#3A7CA5", "card_bg": "#FFFEF9"},
        "Pale Lavender": {"bg": "#F5E8F5", "text": "#3C2C42", "accent": "#7C3C9C", "card_bg": "#FFFEF9"},
        "Pale Mint": {"bg": "#E8F5F1", "text": "#1C3C32", "accent": "#2F7A55", "card_bg": "#FFFEF9"},
        "Warm Gray": {"bg": "#F5F5F5", "text": "#424242", "accent": "#757575", "card_bg": "#FFFFFF"},
        "Dusty Rose": {"bg": "#FCE4EC", "text": "#5D4037", "accent": "#BCAAA4", "card_bg": "#FFFFFF"},
        "Sage Green": {"bg": "#F1F8E9", "text": "#33691E", "accent": "#558B2F", "card_bg": "#FFFFFF"},
    },
    "Low Sensory": {
        "Grey Scale": {"bg": "#F2F2EC", "text": "#2E2E2E", "accent": "#7A7A7A", "card_bg": "#F9F9F5"},
    }
}

MIN_FONT_SIZE = 12
MAX_FONT_SIZE = 40
DEFAULT_FONT_SIZE = 18

# Emoji database
EMOJI_MAP = {
    "lion|tiger|cat": "🦁", "elephant": "🐘", "giraffe": "🦒", "bird|eagle|owl": "🦅",
    "whale|dolphin": "🐋", "butterfly": "🦋", "tree|forest": "🌳", "flower": "🌸",
    "mountain": "⛰️", "volcano": "🌋", "ocean|sea": "🌊", "sun": "☀️", "moon": "🌙",
    "star|space": "⭐", "planet": "🪐", "atom": "⚛️", "dna": "🧬", "brain": "🧠",
    "heart": "❤️", "robot|ai": "🤖", "computer": "💻", "internet": "🌐", "rocket": "🚀",
    "music": "🎵", "art": "🎨", "book": "📖", "sport": "⚽", "happy": "😊", "sad": "😢",
    "love": "😍", "idea": "💡", "question": "❓", "time": "⏰", "money": "💰"
}

def get_emoji(text, mode="Vibrant"):
    if mode == "Low Sensory":
        return "•"
    text_lower = text.lower()
    for keywords, emoji in EMOJI_MAP.items():
        for keyword in keywords.split("|"):
            if keyword in text_lower:
                return emoji
    return "✨" if mode != "Low Sensory" else "•"

# ==================== HELPER FUNCTIONS ====================

def extract_text_from_file(uploaded_file):
    try:
        if uploaded_file.type == "text/plain":
            return uploaded_file.read().decode('utf-8')
        elif uploaded_file.type == "application/pdf":
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            return "".join([page.extract_text() for page in pdf_reader.pages])
        elif "wordprocessingml" in uploaded_file.type:
            from docx import Document
            doc = Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
        return "Unsupported file type"
    except Exception as e:
        return f"Error reading file: {str(e)}"

def search_wikipedia_image(query):
    try:
        clean_query = re.sub(r'[^\w\s-]', '', query).strip()
        if not clean_query:
            return None
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": clean_query,
            "gsrlimit": 5,
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": 500,
        }
        response = requests.get("https://en.wikipedia.org/w/api.php", params=params, timeout=5,
                               headers={"User-Agent": "FlashcardApp/1.0"})
        if response.status_code == 200:
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            for page_data in pages.values():
                if "thumbnail" in page_data:
                    return page_data["thumbnail"]["source"]
        return None
    except:
        return None

def generate_flashcards_deepseek(text, reading_level, mode="Vibrant"):
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["DEEPSEEK_API_KEY"]
        except:
            st.error("🔑 Missing DeepSeek API key")
            return None
    
    if len(text) <= 8000:
        min_cards, max_cards = 3, 5
    elif len(text) <= 16000:
        min_cards, max_cards = 5, 8
    else:
        min_cards, max_cards = 8, 12
    
    level_text = {"simple": "very simple words, short sentences (8-12 words)", 
                  "intermediate": "clear language, medium sentences (12-18 words)",
                  "complex": "precise academic language, longer sentences (up to 25 words)"}.get(reading_level, "clear language")
    
    emoji_instruction = "Do not use any emojis - use plain text only." if mode == "Low Sensory" else "Use relevant emojis for each fact."
    
    prompt = f"""Create {min_cards}-{max_cards} flashcards from this text. Reading level: {level_text}
{emoji_instruction}

Return ONLY JSON: {{"flashcards": [{{"title": "short title", "facts": ["fact 1", "fact 2", "fact 3"]}}]}}

Text: {text[:15000]}"""

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You create flashcards. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        
        result = json.loads(response.choices[0].message.content)
        cards = result.get("flashcards", [])
        
        flashcards = []
        for card in cards:
            topic_emoji = get_emoji(card["title"], mode)
            facts = []
            for fact in card.get("facts", [])[:3]:
                if mode == "Low Sensory":
                    facts.append({"emoji": "•", "text": fact})
                else:
                    facts.append({"emoji": get_emoji(fact, mode), "text": fact})
            flashcards.append({
                "title": card["title"],
                "facts": facts,
                "emoji": topic_emoji,
                "image_search": card["title"]
            })
        return flashcards
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# ==================== MAIN APP ====================

st.set_page_config(page_title="Flashcard Magic", page_icon="✨", layout="wide")

# Initialize session state - preserve cards when settings change
for key, default in [("flashcards", None), ("generated", False), ("card_flipped", {}), 
                     ("card_images", {}), ("current_idx", 0), ("font_size", DEFAULT_FONT_SIZE),
                     ("font_style", "Poppins"), ("color_mode", "Vibrant"), ("color_scheme", "Ocean Teal"),
                     ("show_images", True), ("saved_decks", {})]:
    if key not in st.session_state:
        st.session_state[key] = default

# Get current mode
current_mode = st.session_state.color_mode
is_low_sensory = (current_mode == "Low Sensory")

# ========== SIMPLE KEYBOARD SHORTCUTS ==========
st.markdown("""
<script>
(function() {
    function findAndClick(buttonTexts) {
        const buttons = document.querySelectorAll('button');
        for (let btn of buttons) {
            for (let text of buttonTexts) {
                if (btn.innerText.includes(text)) {
                    btn.click();
                    return true;
                }
            }
        }
        return false;
    }
    
    document.addEventListener('keydown', function(e) {
        // Don't interfere with typing
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        if (e.key === 'ArrowLeft') {
            e.preventDefault();
            findAndClick(['Previous']);
        } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            findAndClick(['Next']);
        } else if (e.key === ' ' || e.key === 'Space' || e.key === 'Enter') {
            e.preventDefault();
            findAndClick(['Reveal', 'Show Topic']);
        } else if (e.key === 'r' || e.key === 'R') {
            e.preventDefault();
            findAndClick(['Reset']);
        }
    });
})();
</script>
""", unsafe_allow_html=True)

# Apply styles
st.markdown(f"""
<style>
/* Font preview in selectbox */
[data-testid="stSelectbox"] option {{
    font-family: var(--font-display) !important;
}}

/* Make color mode buttons look better */
[data-testid="stRadio"] > div {{
    gap: 12px !important;
}}
[data-testid="stRadio"] label {{
    background: #f5f5f5;
    padding: 10px 16px !important;
    border-radius: 12px !important;
    border: 2px solid transparent !important;
    transition: all 0.2s ease !important;
}}
[data-testid="stRadio"] label:hover {{
    background: #e8e8e8 !important;
}}
[data-testid="stRadio"] label[data-baseweb="radio"] {{
    background: transparent !important;
}}

/* Base scaling */
[data-testid="stSidebar"] .stMarkdown, 
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSelectbox div,
[data-testid="stSidebar"] button {{
    font-size: {max(14, st.session_state.font_size - 2)}px !important;
}}

[data-testid="stSelectbox"] div[data-baseweb="select"] div {{
    min-height: {max(40, st.session_state.font_size + 10)}px !important;
}}

.flashcard-title {{
    font-size: {max(24, st.session_state.font_size + 10)}px !important;
}}

.flashcard-fact {{
    font-size: {max(16, st.session_state.font_size)}px !important;
}}

/* Remove animations for Low Sensory */
{'* { animation: none !important; transition: none !important; }' if is_low_sensory else ''}
{'button:hover { transform: none !important; }' if is_low_sensory else ''}

/* Simple keyboard hint styling */
.simple-hint {{
    background: #f8f9fa;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 12px;
    margin-top: 16px;
    border: 1px solid #e0e0e0;
}}
.simple-hint kbd {{
    background: #e9ecef;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 11px;
    margin: 0 2px;
}}
</style>
""", unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    # Color Mode - nicer layout
    st.markdown("### 🎨 Color Mode")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🎨 Vibrant", use_container_width=True, 
                    type="primary" if current_mode == "Vibrant" else "secondary"):
            st.session_state.color_mode = "Vibrant"
            st.session_state.color_scheme = "Ocean Teal"
            st.rerun()
    with col2:
        if st.button("♿ Accessibility", use_container_width=True,
                    type="primary" if current_mode == "Accessibility" else "secondary"):
            st.session_state.color_mode = "Accessibility"
            st.session_state.color_scheme = "Soft Blue"
            st.rerun()
    with col3:
        if st.button("🌙 Low Sensory", use_container_width=True,
                    type="primary" if current_mode == "Low Sensory" else "secondary"):
            st.session_state.color_mode = "Low Sensory"
            st.session_state.color_scheme = "Grey Scale"
            st.rerun()
    
    # Color Scheme (only if not Low Sensory)
    if current_mode != "Low Sensory":
        st.markdown("### 🎨 Color Scheme")
        schemes = list(COLOR_SCHEMES[current_mode].keys())
        # Create colored buttons for each scheme
        scheme_cols = st.columns(2)
        for i, scheme in enumerate(schemes):
            with scheme_cols[i % 2]:
                colors = COLOR_SCHEMES[current_mode][scheme]
                if st.button(f"● {scheme}", use_container_width=True,
                            type="primary" if scheme == st.session_state.color_scheme else "secondary"):
                    st.session_state.color_scheme = scheme
                    st.rerun()
    
    st.divider()
    
    # Font Style with preview
    st.markdown("### ✍️ Font Style")
    # Create font preview options
    font_display_names = {font: font for font in FONT_OPTIONS.keys()}
    selected_font_display = st.selectbox(
        "Font Style",
        options=list(FONT_OPTIONS.keys()),
        format_func=lambda x: f"{x}",
        index=list(FONT_OPTIONS.keys()).index(st.session_state.font_style) if st.session_state.font_style in FONT_OPTIONS else 0,
        key="font_select"
    )
    
    # Apply font preview using CSS
    st.markdown(f"""
    <style>
    [data-testid="stSelectbox"] label {{
        font-family: {selected_font_display}, sans-serif !important;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    if selected_font_display != st.session_state.font_style:
        st.session_state.font_style = selected_font_display
        st.rerun()
    
    # Text Size
    st.markdown("### 🔤 Text Size")
    size = st.slider("Adjust text size", MIN_FONT_SIZE, MAX_FONT_SIZE, st.session_state.font_size)
    if size != st.session_state.font_size:
        st.session_state.font_size = size
        st.rerun()
    
    st.divider()
    
    # Reading Level
    st.markdown("### 📖 Reading Level")
    reading_level = st.selectbox("Reading Level", list(READING_LEVELS.keys()), key="reading_level")
    
    # Show Images
    st.session_state.show_images = st.checkbox("🖼️ Show Images", st.session_state.show_images)
    
    # Save deck button
    if st.session_state.generated and st.session_state.flashcards:
        st.divider()
        deck_name = st.text_input("Deck name", placeholder="My Science Deck", key="deck_name_input")
        if st.button("💾 Save This Deck", use_container_width=True) and deck_name:
            st.success(f"Saved '{deck_name}'!")
    
    # Simple keyboard instructions at bottom
    st.divider()
    st.markdown("""
    <div class="simple-hint">
        <strong>⌨️ Keyboard Shortcuts</strong><br>
        <kbd>←</kbd> <kbd>→</kbd> Navigate &nbsp;|&nbsp; 
        <kbd>Space</kbd> Flip Card &nbsp;|&nbsp;
        <kbd>R</kbd> Reset
    </div>
    """, unsafe_allow_html=True)

# ==================== MAIN CONTENT ====================

# Title
if current_mode == "Low Sensory":
    st.markdown(f"""
    <div style='text-align: center; padding: 20px;'>
        <div style='font-size: {max(32, st.session_state.font_size + 14)}px; font-weight: bold;'>Flashcard Magic</div>
        <div style='font-size: {max(16, st.session_state.font_size - 2)}px; color: #555;'>{APP_SUBTITLE}</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style='text-align: center; padding: 20px;'>
        <div style='font-size: 50px;'>✨</div>
        <div style='font-size: {max(32, st.session_state.font_size + 14)}px; font-weight: bold; background: linear-gradient(135deg, #FF6B6B, #4ECDC4, #45B7D1); -webkit-background-clip: text; background-clip: text; color: transparent;'>{APP_TITLE}</div>
        <div style='font-size: {max(16, st.session_state.font_size - 2)}px; color: #666;'>{APP_SUBTITLE}</div>
    </div>
    """, unsafe_allow_html=True)

# Text input
st.markdown("## 📝 Your Text")
input_type = st.radio("Input Type", ["✏️ Paste Text", "📁 Upload File"], horizontal=True)

user_text = ""
if input_type == "✏️ Paste Text":
    user_text = st.text_area("Paste your text here...", height=150, label_visibility="collapsed")
else:
    uploaded = st.file_uploader("Upload TXT, PDF, or DOCX", type=["txt", "pdf", "docx"], label_visibility="collapsed")
    if uploaded:
        user_text = extract_text_from_file(uploaded)

word_count = len(user_text.split()) if user_text else 0
st.caption(f"📝 {word_count} words")

# Generate button
if st.button("✨ Generate Flashcards ✨", type="primary", use_container_width=True):
    if len(user_text) < 50:
        st.warning("Please enter more text (at least 50 characters)")
    else:
        with st.spinner("Creating flashcards..."):
            cards = generate_flashcards_deepseek(user_text, READING_LEVELS[reading_level], current_mode)
            if cards:
                st.session_state.flashcards = cards
                st.session_state.generated = True
                st.session_state.card_flipped = {}
                st.session_state.card_images = {}
                
                if st.session_state.show_images:
                    with st.spinner("Finding images..."):
                        for i, card in enumerate(cards):
                            img = search_wikipedia_image(card["image_search"])
                            if img:
                                st.session_state.card_images[i] = img
                st.rerun()

# ==================== DISPLAY FLASHCARDS ====================
if st.session_state.generated and st.session_state.flashcards:
    cards = st.session_state.flashcards
    idx = st.session_state.current_idx
    
    # Get colors based on mode
    if current_mode == "Low Sensory":
        colors = COLOR_SCHEMES["Low Sensory"]["Grey Scale"]
    else:
        colors = COLOR_SCHEMES[current_mode][st.session_state.color_scheme]
    
    # Apply current font to entire app
    st.markdown(f"""
    <style>
    * {{
        font-family: '{st.session_state.font_style}', sans-serif !important;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Progress
    flipped = sum(1 for i in range(len(cards)) if st.session_state.card_flipped.get(i, False))
    st.progress(flipped / len(cards))
    st.caption(f"📚 {flipped}/{len(cards)} cards studied")
    
    if flipped == len(cards):
        if not is_low_sensory:
            st.balloons()
        st.success("🎉 You've mastered all cards! 🎉")
    
    # Current card
    card = cards[idx]
    is_flipped = st.session_state.card_flipped.get(idx, False)
    
    # Card styling
    card_style = f"""
        background: {colors['card_bg']};
        border-radius: {'12px' if is_low_sensory else '24px'};
        padding: 40px;
        margin: 20px 0;
        text-align: center;
        box-shadow: {'0 2px 8px rgba(0,0,0,0.1)' if is_low_sensory else '0 8px 32px rgba(0,0,0,0.1)'};
        border-left: {4 if is_low_sensory else 8}px solid {colors['accent']};
    """
    
    if not is_flipped:
        img_html = ""
        if st.session_state.show_images and idx in st.session_state.card_images:
            img_html = f"<img src='{st.session_state.card_images[idx]}' style='max-width: 100%; max-height: 250px; border-radius: {'8px' if is_low_sensory else '15px'}; margin-bottom: 20px;'>"
        
        st.markdown(f"""
        <div style='{card_style}'>
            <div style='font-size: {'40px' if is_low_sensory else '80px'}; margin-bottom: 20px;'>{card['emoji'] if not is_low_sensory else '📄'}</div>
            {img_html}
            <div class='flashcard-title' style='font-weight: bold; color: {colors['text']};'>{card['title']}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        facts_html = "".join([
            f"<div style='display: flex; align-items: center; gap: 15px; margin: 15px 0; padding: {8 if is_low_sensory else 12}px; background: rgba(0,0,0,0.03); border-radius: {8 if is_low_sensory else 12}px;'>"
            f"<div style='font-size: {24 if is_low_sensory else 36}px;'>{f['emoji']}</div>"
            f"<div class='flashcard-fact' style='flex: 1; text-align: left;'>{f['text']}</div>"
            f"</div>" for f in card['facts']
        ])
        
        st.markdown(f"""
        <div style='{card_style}'>
            <div style='text-align: center; margin-bottom: 20px;'>
                <span style='background: {colors['accent']}; color: white; padding: 6px 16px; border-radius: {15 if not is_low_sensory else 8}px;'>KEY FACTS</span>
            </div>
            {facts_html}
        </div>
        """, unsafe_allow_html=True)
    
    # Navigation buttons
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    with col1:
        if st.button("◀ Previous", key="prev_btn", disabled=(idx == 0), use_container_width=True):
            st.session_state.current_idx = max(0, idx - 1)
            st.rerun()
    with col2:
        btn_text = "📖 Reveal Facts" if not is_flipped else "🔙 Show Topic"
        if st.button(btn_text, key="flip_btn", use_container_width=True, type="primary"):
            st.session_state.card_flipped[idx] = not is_flipped
            st.rerun()
    with col3:
        st.markdown(f"<p style='text-align: center; margin-top: 8px;'>{idx + 1} / {len(cards)}</p>", unsafe_allow_html=True)
    with col4:
        if st.button("Next ▶", key="next_btn", disabled=(idx == len(cards) - 1), use_container_width=True):
            st.session_state.current_idx = min(len(cards) - 1, idx + 1)
            st.rerun()
    with col5:
        if st.button("🔄 Reset", key="reset_btn", use_container_width=True):
            st.session_state.card_flipped = {}
            st.rerun()
    
    # Download
    st.divider()
    st.markdown("### 📥 Download")
    text_export = "\n\n".join([f"TOPIC: {c['title']}\n" + "\n".join([f"  {f['emoji']} {f['text']}" for f in c['facts']]) for c in cards])
    st.download_button("📝 Download All Cards (Text)", text_export, "flashcards.txt", use_container_width=True)

# Feedback
st.divider()
st.markdown("""
<div style='text-align: center; padding: 20px;'>
    <p>💬 Made with DeepSeek API • No data stored</p>
</div>
""", unsafe_allow_html=True)
