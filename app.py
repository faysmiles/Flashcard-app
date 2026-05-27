# app.py - CLEAN WORKING VERSION (No keyboard bugs)
# Copy this entire code into app.py

import streamlit as st
import os
import re
import json
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
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

FONT_OPTIONS = ["Poppins", "OpenDyslexic", "Lexend", "Verdana", "Arial", "Comic Sans MS", "Nunito", "Montserrat", "Roboto", "Inter"]

COLOR_SCHEMES = {
    "Vibrant": {
        "Ocean Teal": {"bg": "#E0F7FA", "text": "#004D40", "accent": "#00897B", "card_bg": "#FFFFFF"},
        "Forest Green": {"bg": "#E8F5E9", "text": "#1B5E20", "accent": "#43A047", "card_bg": "#FFFFFF"},
        "Berry Pink": {"bg": "#FCE4EC", "text": "#880E4F", "accent": "#D81B60", "card_bg": "#FFFFFF"},
        "Sky Blue": {"bg": "#E3F2FD", "text": "#0D47A1", "accent": "#1E88E5", "card_bg": "#FFFFFF"},
    },
    "Accessibility": {
        "Soft Blue": {"bg": "#E8F1F5", "text": "#1C3A42", "accent": "#3A7CA5", "card_bg": "#FFFEF9"},
        "Pale Lavender": {"bg": "#F5E8F5", "text": "#3C2C42", "accent": "#7C3C9C", "card_bg": "#FFFEF9"},
        "Pale Mint": {"bg": "#E8F5F1", "text": "#1C3C32", "accent": "#2F7A55", "card_bg": "#FFFEF9"},
        "Warm Gray": {"bg": "#F5F5F5", "text": "#424242", "accent": "#757575", "card_bg": "#FFFFFF"},
    },
    "Low Sensory": {
        "Grey Scale": {"bg": "#F2F2EC", "text": "#2E2E2E", "accent": "#7A7A7A", "card_bg": "#F9F9F5"},
    }
}

MIN_FONT_SIZE = 12
MAX_FONT_SIZE = 40
DEFAULT_FONT_SIZE = 18

EMOJI_MAP = {
    "lion|tiger|cat": "🦁", "elephant": "🐘", "giraffe": "🦒", "bird|eagle|owl": "🦅",
    "whale|dolphin": "🐋", "butterfly": "🦋", "tree|forest": "🌳", "flower": "🌸",
    "mountain": "⛰️", "ocean|sea": "🌊", "sun": "☀️", "moon": "🌙", "star|space": "⭐",
    "atom": "⚛️", "dna": "🧬", "brain": "🧠", "heart": "❤️", "robot|ai": "🤖",
    "computer": "💻", "music": "🎵", "art": "🎨", "book": "📖", "idea": "💡"
}

def get_emoji(text, mode="Vibrant"):
    if mode == "Low Sensory":
        return "•"
    text_lower = text.lower()
    for keywords, emoji in EMOJI_MAP.items():
        for keyword in keywords.split("|"):
            if keyword in text_lower:
                return emoji
    return "✨"

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
        return f"Error: {str(e)}"

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
            st.error("🔑 Missing DeepSeek API key. Get one at platform.deepseek.com")
            return None
    
    if len(text) <= 8000:
        min_cards, max_cards = 3, 5
    elif len(text) <= 16000:
        min_cards, max_cards = 5, 8
    else:
        min_cards, max_cards = 8, 12
    
    level_text = {"simple": "very simple words, short sentences", 
                  "intermediate": "clear language, medium sentences",
                  "complex": "precise academic language"}.get(reading_level, "clear language")
    
    emoji_instruction = "Do not use any emojis - use plain text only." if mode == "Low Sensory" else "Use relevant emojis"
    
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

# Initialize session state
if "flashcards" not in st.session_state:
    st.session_state.flashcards = None
if "generated" not in st.session_state:
    st.session_state.generated = False
if "card_flipped" not in st.session_state:
    st.session_state.card_flipped = {}
if "card_images" not in st.session_state:
    st.session_state.card_images = {}
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0
if "font_size" not in st.session_state:
    st.session_state.font_size = DEFAULT_FONT_SIZE
if "font_style" not in st.session_state:
    st.session_state.font_style = "Poppins"
if "color_mode" not in st.session_state:
    st.session_state.color_mode = "Vibrant"
if "color_scheme" not in st.session_state:
    st.session_state.color_scheme = "Ocean Teal"
if "show_images" not in st.session_state:
    st.session_state.show_images = True

current_mode = st.session_state.color_mode
is_low_sensory = (current_mode == "Low Sensory")

# Apply styles based on settings
colors = COLOR_SCHEMES[current_mode][st.session_state.color_scheme] if current_mode != "Low Sensory" else COLOR_SCHEMES["Low Sensory"]["Grey Scale"]

st.markdown(f"""
<style>
/* Global font */
* {{
    font-family: '{st.session_state.font_style}', sans-serif !important;
}}

/* Background */
[data-testid="stAppViewContainer"] {{
    background-color: {colors['bg']} !important;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background-color: {colors['bg']} !important;
}}

/* Text colors */
p, span, li, label, .stMarkdown {{
    color: {colors['text']} !important;
}}

/* Headers */
h1, h2, h3, h4, h5, h6 {{
    color: {colors['accent']} !important;
}}

/* Buttons */
.stButton button {{
    background-color: {colors['accent']} !important;
    color: white !important;
    border-radius: 12px !important;
    padding: 8px 16px !important;
}}

.stButton button:hover {{
    opacity: 0.85 !important;
}}

/* Remove animations for Low Sensory */
{'* { animation: none !important; transition: none !important; }' if is_low_sensory else ''}

/* Text size */
p, span, li, label {{
    font-size: {st.session_state.font_size}px !important;
}}
</style>
""", unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    # Color Mode
    st.markdown("### Color Mode")
    mode_options = ["Vibrant", "Accessibility", "Low Sensory"]
    for mode in mode_options:
        if st.button(mode, use_container_width=True, type="primary" if st.session_state.color_mode == mode else "secondary"):
            st.session_state.color_mode = mode
            if mode == "Low Sensory":
                st.session_state.color_scheme = "Grey Scale"
            else:
                st.session_state.color_scheme = list(COLOR_SCHEMES[mode].keys())[0]
            st.rerun()
    
    # Color Scheme (only if not Low Sensory)
    if current_mode != "Low Sensory":
        st.markdown("### Color Scheme")
        schemes = list(COLOR_SCHEMES[current_mode].keys())
        for scheme in schemes:
            if st.button(scheme, use_container_width=True, type="primary" if scheme == st.session_state.color_scheme else "secondary"):
                st.session_state.color_scheme = scheme
                st.rerun()
    
    st.divider()
    
    # Font Style
    st.markdown("### Font Style")
    selected_font = st.selectbox("Choose a font", FONT_OPTIONS, index=FONT_OPTIONS.index(st.session_state.font_style))
    if selected_font != st.session_state.font_style:
        st.session_state.font_style = selected_font
        st.rerun()
    
    # Text Size
    st.markdown("### Text Size")
    new_size = st.slider("Adjust size", MIN_FONT_SIZE, MAX_FONT_SIZE, st.session_state.font_size)
    if new_size != st.session_state.font_size:
        st.session_state.font_size = new_size
        st.rerun()
    
    st.divider()
    
    # Reading Level
    st.markdown("### Reading Level")
    reading_level = st.selectbox("Choose level", list(READING_LEVELS.keys()))
    
    # Show Images
    st.session_state.show_images = st.checkbox("Show Images", st.session_state.show_images)
    
    st.divider()
    st.caption("💡 Settings change instantly")
    st.caption("🎴 Cards are preserved when changing settings")

# ==================== MAIN CONTENT ====================

# Title
if current_mode == "Low Sensory":
    st.markdown(f"""
    <div style='text-align: center; padding: 20px;'>
        <div style='font-size: 48px; font-weight: bold;'>Flashcard Magic</div>
        <div style='font-size: 18px;'>{APP_SUBTITLE}</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style='text-align: center; padding: 20px;'>
        <div style='font-size: 64px;'>✨</div>
        <div style='font-size: 48px; font-weight: bold;'>{APP_TITLE}</div>
        <div style='font-size: 18px;'>{APP_SUBTITLE}</div>
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
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
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
                    st.session_state.current_idx = 0
                    
                    if st.session_state.show_images:
                        with st.spinner("Finding images..."):
                            for i, card in enumerate(cards):
                                img = search_wikipedia_image(card["image_search"])
                                if img:
                                    st.session_state.card_images[i] = img
                    st.rerun()

# Display flashcards
if st.session_state.generated and st.session_state.flashcards:
    cards = st.session_state.flashcards
    idx = st.session_state.current_idx
    colors = COLOR_SCHEMES[current_mode][st.session_state.color_scheme] if current_mode != "Low Sensory" else COLOR_SCHEMES["Low Sensory"]["Grey Scale"]
    
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
        border-radius: 20px;
        padding: 40px;
        margin: 20px 0;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-left: 6px solid {colors['accent']};
    """
    
    if not is_flipped:
        img_html = ""
        if st.session_state.show_images and idx in st.session_state.card_images and st.session_state.card_images[idx]:
            img_html = f"<img src='{st.session_state.card_images[idx]}' style='max-width: 100%; max-height: 250px; border-radius: 12px; margin-bottom: 20px;'>"
        
        st.markdown(f"""
        <div style='{card_style}'>
            <div style='font-size: 60px; margin-bottom: 20px;'>{card['emoji']}</div>
            {img_html}
            <div style='font-size: 28px; font-weight: bold; color: {colors['text']};'>{card['title']}</div>
            <div style='margin-top: 30px; color: {colors['accent']};'>Click "Reveal Facts" to see more</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        facts_html = "".join([
            f"<div style='display: flex; align-items: center; gap: 15px; margin: 12px 0; padding: 12px; background: rgba(0,0,0,0.03); border-radius: 10px;'>"
            f"<div style='font-size: 28px;'>{f['emoji']}</div>"
            f"<div style='flex: 1; text-align: left; font-size: {st.session_state.font_size}px;'>{f['text']}</div>"
            f"</div>" for f in card['facts']
        ])
        
        st.markdown(f"""
        <div style='{card_style}'>
            <div style='text-align: center; margin-bottom: 20px;'>
                <span style='background: {colors['accent']}; color: white; padding: 6px 16px; border-radius: 20px;'>KEY FACTS</span>
            </div>
            {facts_html}
        </div>
        """, unsafe_allow_html=True)
    
    # Navigation buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("◀ Previous", disabled=(idx == 0), use_container_width=True):
            st.session_state.current_idx = max(0, idx - 1)
            st.rerun()
    with col2:
        btn_text = "📖 Reveal Facts" if not is_flipped else "🔙 Show Topic"
        if st.button(btn_text, use_container_width=True, type="primary"):
            st.session_state.card_flipped[idx] = not is_flipped
            st.rerun()
    with col3:
        st.markdown(f"<p style='text-align: center; margin-top: 8px;'>{idx + 1} / {len(cards)}</p>", unsafe_allow_html=True)
    with col4:
        if st.button("Next ▶", disabled=(idx == len(cards) - 1), use_container_width=True):
            st.session_state.current_idx = min(len(cards) - 1, idx + 1)
            st.rerun()
    
    # Reset button
    if st.button("🔄 Reset All Cards", use_container_width=True):
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
    <p>💬 Made with DeepSeek API • No data stored • Your privacy is protected</p>
</div>
""", unsafe_allow_html=True)
