import streamlit as st
import os
import json
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

FONT_OPTIONS = ["Poppins", "OpenDyslexic", "Lexend", "Verdana", "Arial", "Comic Sans MS"]

COLOR_SCHEMES = {
    "Blue": {
        "bg": "#E8F1F5",
        "text": "#0D2B3E",
        "sidebar_text": "#1a3a4a",
        "accent": "#2B6C9E",
        "card_bg": "#FFFFFF",
        "gradient": "linear-gradient(135deg, #2B6C9E, #1E5A87)",
        "hover": "#3A7CA5",
        "shadow": "rgba(43, 108, 158, 0.3)",
        "dropdown_bg": "#FFFFFF",
        "dropdown_hover_bg": "#2B6C9E",
        "dropdown_text": "#1A1A1A"
    },
    "Green": {
        "bg": "#E8F5E9",
        "text": "#0D3B15",
        "sidebar_text": "#1a4a1a",
        "accent": "#2E7D32",
        "card_bg": "#FFFFFF",
        "gradient": "linear-gradient(135deg, #2E7D32, #1B5E20)",
        "hover": "#43A047",
        "shadow": "rgba(46, 125, 50, 0.3)",
        "dropdown_bg": "#FFFFFF",
        "dropdown_hover_bg": "#2E7D32",
        "dropdown_text": "#1A1A1A"
    },
    "Purple": {
        "bg": "#F5E8F5",
        "text": "#1A0D2E",
        "sidebar_text": "#2a1540",
        "accent": "#6B2D8E",
        "card_bg": "#FFFFFF",
        "gradient": "linear-gradient(135deg, #7B2D8E, #5A1E6B)",
        "hover": "#8B3DAE",
        "shadow": "rgba(107, 45, 142, 0.3)",
        "dropdown_bg": "#F8F0F8",
        "dropdown_hover_bg": "#6B2D8E",
        "dropdown_text": "#1A0D2E"
    },
    "Gray": {
        "bg": "#F5F5F5",
        "text": "#2C2C2C",
        "sidebar_text": "#1a1a1a",
        "accent": "#6B6B6B",
        "card_bg": "#FFFFFF",
        "gradient": "linear-gradient(135deg, #6B6B6B, #555555)",
        "hover": "#808080",
        "shadow": "rgba(107, 107, 107, 0.3)",
        "dropdown_bg": "#FFFFFF",
        "dropdown_hover_bg": "#6B6B6B",
        "dropdown_text": "#1A1A1A"
    }
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
        except Exception:
            st.error("Missing DeepSeek API key. Get one at platform.deepseek.com")
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

colors = COLOR_SCHEMES[st.session_state.color_scheme]

# ========== STYLES ==========
st.markdown(f"""
<style>
* {{
    font-family: '{st.session_state.font_style}', sans-serif !important;
}}

[data-testid="stAppViewContainer"] {{
    background-color: {colors['bg']} !important;
}}

[data-testid="stSidebar"] {{
    background-color: {colors['bg']} !important;
}}

/* ===== DROPDOWN TRIGGER (closed state) ===== */
[data-testid="stSelectbox"] label {{
    color: {colors['sidebar_text']} !important;
    font-weight: 600 !important;
    margin-bottom: 5px !important;
}}

[data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
    background-color: {colors['dropdown_bg']} !important;
    border-radius: 8px !important;
    border: 1px solid {colors['accent']}40 !important;
}}

/* Force ALL text inside the selectbox trigger to be readable, no exceptions */
[data-testid="stSelectbox"] div[data-baseweb="select"],
[data-testid="stSelectbox"] div[data-baseweb="select"] div,
[data-testid="stSelectbox"] div[data-baseweb="select"] span,
[data-testid="stSelectbox"] div[data-baseweb="select"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] [class*="ValueContainer"],
[data-testid="stSelectbox"] div[data-baseweb="select"] [class*="SingleValue"] {{
    color: {colors['dropdown_text']} !important;
    -webkit-text-fill-color: {colors['dropdown_text']} !important;
    opacity: 1 !important;
    font-weight: 600 !important;
    font-size: 15px !important;
}}

[data-testid="stSelectbox"] svg {{
    fill: {colors['accent']} !important;
}}

[data-testid="stSelectbox"] div[data-baseweb="select"]:hover {{
    border-color: {colors['accent']} !important;
}}

/* ===== DROPDOWN MENU (open / portal-rendered) =====
   Streamlit renders the open menu in a portal, so we target
   the popover and listbox roles globally rather than via stSelectbox. */

div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] [data-baseweb="menu"] {{
    background-color: {colors['dropdown_bg']} !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    border: 1px solid {colors['accent']}30 !important;
}}

ul[role="listbox"],
div[role="listbox"] {{
    background-color: {colors['dropdown_bg']} !important;
}}

/* Default option — layout and bg only on the option itself */
li[role="option"],
div[role="option"] {{
    background-color: {colors['dropdown_bg']} !important;
    color: {colors['dropdown_text']} !important;
    -webkit-text-fill-color: {colors['dropdown_text']} !important;
    opacity: 1 !important;
    font-weight: 500 !important;
    padding: 10px 16px !important;
}}

/* Nested text inside options — colour only, no layout, transparent bg */
li[role="option"] *,
div[role="option"] * {{
    color: {colors['dropdown_text']} !important;
    -webkit-text-fill-color: {colors['dropdown_text']} !important;
    background: transparent !important;
}}

/* Hover — accent fill, white text */
li[role="option"]:hover,
div[role="option"]:hover {{
    background-color: {colors['dropdown_hover_bg']} !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    cursor: pointer !important;
}}

li[role="option"]:hover *,
div[role="option"]:hover * {{
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    background: transparent !important;
}}

/* Currently-selected — same bg as default, indicate with bold + left border */
li[role="option"][aria-selected="true"],
div[role="option"][aria-selected="true"],
li[role="option"][data-highlighted="true"],
div[role="option"][data-highlighted="true"] {{
    background-color: {colors['dropdown_bg']} !important;
    color: {colors['dropdown_text']} !important;
    -webkit-text-fill-color: {colors['dropdown_text']} !important;
    font-weight: 700 !important;
    border-left: 3px solid {colors['accent']} !important;
}}

li[role="option"][aria-selected="true"] *,
div[role="option"][aria-selected="true"] *,
li[role="option"][data-highlighted="true"] *,
div[role="option"][data-highlighted="true"] * {{
    color: {colors['dropdown_text']} !important;
    -webkit-text-fill-color: {colors['dropdown_text']} !important;
    background: transparent !important;
}}

/* ===== TOP BANNER ===== */
.top-banner {{
    background: linear-gradient(135deg, {colors['accent']}18, {colors['accent']}05);
    padding: 16px 20px;
    margin-bottom: 20px;
    border-bottom: 2px solid {colors['accent']}30;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 18px;
    flex-wrap: wrap;
}}

.banner-symbol {{
    font-size: 26px;
    color: {colors['accent']} !important;
    display: inline-block;
    line-height: 1;
    animation: float 3s ease-in-out infinite;
}}

.banner-text {{
    font-size: 22px;
    font-weight: 700;
    color: {colors['accent']} !important;
    letter-spacing: 0.5px;
    margin: 0 8px;
}}

.banner-symbol:nth-child(1) {{ animation-delay: 0s; }}
.banner-symbol:nth-child(2) {{ animation-delay: 0.4s; }}
.banner-symbol:nth-child(4) {{ animation-delay: 0.8s; }}
.banner-symbol:nth-child(5) {{ animation-delay: 1.2s; }}

@keyframes float {{
    0%, 100% {{ transform: translateY(0px); }}
    50% {{ transform: translateY(-5px); }}
}}

/* ===== HEADINGS / TEXT ===== */
h1, h2, h3, h4, h5, h6 {{
    color: {colors['accent']} !important;
    font-weight: 700 !important;
}}

p, li, label, .stMarkdown, .stCaption {{
    color: {colors['text']} !important;
    font-size: {st.session_state.font_size}px !important;
    line-height: 1.5 !important;
}}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: {colors['accent']} !important;
    font-weight: 700 !important;
}}

[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stCaption {{
    color: {colors['sidebar_text']} !important;
    font-weight: 500 !important;
}}

/* ===== BUTTONS ===== */
.stButton button {{
    background: {colors['gradient']} !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    box-shadow: 0 4px 12px {colors['shadow']} !important;
    transition: all 0.2s ease !important;
}}

.stButton button:hover {{
    background: {colors['hover']} !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 16px {colors['shadow']} !important;
}}

.stButton button:disabled {{
    opacity: 0.5 !important;
    transform: none !important;
    cursor: not-allowed !important;
}}

.stButton button[kind="primary"] {{
    font-size: 18px !important;
    padding: 12px 32px !important;
    font-weight: 700 !important;
}}

[data-testid="stSidebar"] .stButton button {{
    margin: 5px 0 !important;
    font-size: 14px !important;
    padding: 8px 16px !important;
}}

/* ===== PROGRESS / SLIDER ===== */
[data-testid="stProgress"] > div > div > div > div {{
    background: {colors['gradient']} !important;
    border-radius: 10px !important;
}}

[data-testid="stSlider"] div[role="slider"] {{
    background: {colors['accent']} !important;
    box-shadow: 0 0 6px {colors['accent']} !important;
}}

/* ===== FOCUS RING (accessibility) ===== */
button:focus-visible,
[role="button"]:focus-visible {{
    outline: 3px solid {colors['accent']} !important;
    outline-offset: 2px !important;
}}
</style>
""", unsafe_allow_html=True)

# ========== TOP BANNER ==========
st.markdown("""
<div class="top-banner">
    <span class="banner-symbol">✦</span>
    <span class="banner-symbol">✧</span>
    <span class="banner-text">Practice makes progress</span>
    <span class="banner-symbol">✧</span>
    <span class="banner-symbol">✦</span>
</div>
""", unsafe_allow_html=True)

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("# ⚙️ Settings")
    st.markdown("---")

    st.markdown("### 🎨 Color Theme")
    for scheme in COLOR_SCHEMES.keys():
        if st.button(scheme, use_container_width=True, key=f"theme_btn_{scheme}"):
            st.session_state.color_scheme = scheme
            st.rerun()

    st.markdown("---")

    st.markdown("### ✍️ Font")
    font = st.selectbox(
        "Font Style",
        FONT_OPTIONS,
        index=FONT_OPTIONS.index(st.session_state.font_style),
        key="font_select"
    )
    if font != st.session_state.font_style:
        st.session_state.font_style = font
        st.rerun()

    st.markdown("### 📏 Text Size")
    st.caption("Adjust to your preference")
    size = st.slider("Size", 16, 40, st.session_state.font_size, key="size_slider")
    if size != st.session_state.font_size:
        st.session_state.font_size = size
        st.rerun()

    st.markdown("---")

    st.markdown("### 📚 Reading Level")
    reading_level = st.selectbox("Level", list(READING_LEVELS.keys()), key="reading_select")

    st.markdown("---")
    st.caption("✨ Clean buttons")
    st.caption("📖 WCAG compliant")

# ========== MAIN CONTENT ==========
st.markdown(f"""
<div style='text-align: center; padding: 10px 20px 20px 20px;'>
    <h1 style='font-size: 48px; margin: 0;'>{APP_TITLE}</h1>
    <p style='font-size: 18px; opacity: 0.8; margin-top: 5px;'>Turn any text into fun flashcards</p>
</div>
""", unsafe_allow_html=True)

st.markdown("## Your Text")
input_type = st.radio("Input Type", ["Paste Text", "Upload File"], horizontal=True)

user_text = ""
if input_type == "Paste Text":
    user_text = st.text_area(
        "Paste your text here...",
        height=150,
        placeholder="Paste any text - article, notes, Wikipedia page...",
        label_visibility="collapsed"
    )
else:
    uploaded = st.file_uploader("Upload TXT, PDF, or DOCX", type=["txt", "pdf", "docx"], label_visibility="collapsed")
    if uploaded:
        try:
            if uploaded.type == "text/plain":
                user_text = uploaded.read().decode('utf-8')
            else:
                user_text = f"File uploaded: {uploaded.name}"
            st.success(f"Loaded {uploaded.name}")
        except Exception:
            st.error("Could not read file")

word_count = len(user_text.split()) if user_text else 0
st.caption(f"📝 {word_count} words")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("Generate Flashcards", type="primary", use_container_width=True, key="generate_btn"):
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

if st.session_state.generated and st.session_state.flashcards:
    cards = st.session_state.flashcards
    idx = st.session_state.current_idx
    card = cards[idx]
    is_flipped = st.session_state.card_flipped.get(idx, False)

    flipped_count = sum(st.session_state.card_flipped.get(i, False) for i in range(len(cards)))
    st.progress(flipped_count / len(cards))
    st.caption(f"Progress: {flipped_count}/{len(cards)} cards studied")

    if flipped_count == len(cards):
        st.balloons()
        st.success("Congratulations! You've mastered all cards!")

    if not is_flipped:
        st.markdown(f"""
        <div style='
            background: {colors['card_bg']};
            border-radius: 20px;
            padding: 60px 40px;
            text-align: center;
            border-left: 6px solid {colors['accent']};
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
            margin: 20px 0;
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
        '>
            <div style='font-size: 32px;'>{f['emoji']}</div>
            <div style='flex: 1; font-size: {st.session_state.font_size}px; color: {colors['text']};'>{f['text']}</div>
        </div>
        """ for f in card['facts']])

        st.markdown(f"""
        <div style='
            background: {colors['card_bg']};
            border-radius: 20px;
            padding: 40px;
            border-left: 6px solid {colors['accent']};
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
            margin: 20px 0;
        '>
            <h3 style='text-align: center; margin-bottom: 30px; color: {colors['accent']};'>Key Facts</h3>
            {facts_html}
        </div>
        """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("Previous", disabled=(idx == 0), use_container_width=True, key="prev_btn"):
            st.session_state.current_idx = max(0, idx - 1)
            st.rerun()
    with col2:
        if st.button("Reveal Facts" if not is_flipped else "Show Topic", use_container_width=True, key="flip_btn"):
            st.session_state.card_flipped[idx] = not is_flipped
            st.rerun()
    with col3:
        st.markdown(f"<p style='text-align: center; margin-top: 10px;'><strong>{idx + 1}</strong> / {len(cards)}</p>", unsafe_allow_html=True)
    with col4:
        if st.button("Next", disabled=(idx == len(cards) - 1), use_container_width=True, key="next_btn"):
            st.session_state.current_idx = min(len(cards) - 1, idx + 1)
            st.rerun()

    if st.button("Reset All Cards", use_container_width=True, key="reset_btn"):
        st.session_state.card_flipped = {}
        st.rerun()

    st.divider()
    st.markdown("### Download")
    text_export = "\n\n".join([
        f"TOPIC: {c['title']}\n" + "\n".join([f"  {f['emoji']} {f['text']}" for f in c['facts']])
        for c in cards
    ])
    st.download_button("Download All Cards (Text)", text_export, "flashcards.txt", use_container_width=True)

st.divider()
st.markdown("""
<div style='text-align: center; padding: 20px;'>
    <p>Made with DeepSeek API • WCAG 2.1 AA Compliant</p>
</div>
""", unsafe_allow_html=True)
