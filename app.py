import os
from dotenv import load_dotenv

# Load environment variables from .env (for local development)
load_dotenv()

import streamlit as st

# Also load from Streamlit secrets if available (for cloud deployment)
try:
    if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass  # Running locally, .env will be used

# ==================== AUTO-CREATE THEME CONFIG ====================
def create_streamlit_config():
    """Create .streamlit/config.toml automatically at startup"""
    config_dir = os.path.expanduser("~/.streamlit")
    config_file = os.path.join(config_dir, "config.toml")
    
    # Create directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    
    # Write config file
    theme_config = """[theme]
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
"""
    
    with open(config_file, "w") as f:
        f.write(theme_config)

# Create config on startup
create_streamlit_config()

# ==================== IMPORTS FROM config.py ====================
from config import (
    APP_TITLE, APP_SUBTITLE, READING_LEVELS, FONT_OPTIONS,
    MIN_FONT_SIZE, MAX_FONT_SIZE, DEFAULT_FONT_SIZE,
    MIN_IMAGE_STEPS, MAX_IMAGE_STEPS, DEFAULT_IMAGE_STEPS
)
from utils import summarise_text, apply_styles, extract_text_from_file, generate_cartoon_from_reference, generate_simple_flashcards, generate_flashcards_from_llm, evaluate_answer_semantically, generate_mnemonic, generate_wacky_image_from_concept, get_card_colors

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

# Enhanced title with better visual hierarchy
st.markdown(f"""
<style>
.header-container {{
    background: linear-gradient(135deg, #FF6B6B 0%, #FF8787 100%);
    padding: 40px 30px;
    border-radius: 12px;
    margin-bottom: 40px;
    box-shadow: 0 4px 12px rgba(255, 107, 107, 0.15);
}}

.header-title {{
    font-size: 2.8em;
    font-weight: 800;
    color: #FFFFFF;
    margin: 0;
    letter-spacing: -0.5px;
    line-height: 1.1;
}}

.header-subtitle {{
    font-size: 1.1em;
    color: rgba(255, 255, 255, 0.95);
    margin: 12px 0 0 0;
    font-weight: 400;
    line-height: 1.5;
    opacity: 0.9;
}}
</style>

<div class="header-container">
    <h1 class="header-title">💡 {APP_TITLE}</h1>
    <p class="header-subtitle">{APP_SUBTITLE}</p>
</div>
""", unsafe_allow_html=True)

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
        border-left: 4px solid #FF6B6B;
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
        "Generate Images",
        value=False,
        key="make_pictures_check"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Picture quality slider
    if make_pictures:
        st.markdown('<div class="setting-group">', unsafe_allow_html=True)
        st.markdown('<label class="setting-label">Image Quality</label>', unsafe_allow_html=True)
        image_quality = st.slider(
            "Picture Quality (more = better but slower)",
            MIN_IMAGE_STEPS,
            MAX_IMAGE_STEPS,
            DEFAULT_IMAGE_STEPS,
            key="image_quality_slider",
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        image_quality = DEFAULT_IMAGE_STEPS
    
    
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
        background: linear-gradient(135deg, #FF6B6B 0%, #FF5252 100%);
        color: white;
        border: none;
        padding: 16px 48px;
        font-size: 1.05em;
        font-weight: 700;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(255, 107, 107, 0.25);
    }}
    
    .make-flashcard-btn:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(255, 107, 107, 0.35);
    }}
    </style>
    """, unsafe_allow_html=True)
    
    button_col1, button_col2, button_col3 = st.columns([1, 1.2, 1])
    with button_col2:
        if st.button("✨ Make Flashcard", use_container_width=True, key="make_flashcard_btn"):
            if user_text.strip():
                # Get the reading level code (simple/intermediate/complex) from the dropdown
                level_code = READING_LEVELS[reading_level]
                
                # Clear old cards/images when regenerating so reading level change takes effect
                st.session_state.card_images = {}
                st.session_state.card_flipped = {}
                
                # Use LLM to extract flashcards directly at the chosen reading level
                with st.spinner(f"🤖 AI is creating {reading_level.split('(')[0].strip()} flashcards..."):
                    from utils import generate_flashcards_from_llm
                    flashcards = generate_flashcards_from_llm(user_text, reading_level=level_code)
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
            border-bottom: 3px solid #FF6B6B;
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
        
        # Display simple flashcards: Title (front) ↔ Facts + Image (back)
        for idx, card in enumerate(flashcards):
            is_flipped = st.session_state.card_flipped.get(idx, False)
            
            # Get colors
            bg_color = card_colors['flipped_bg'] if is_flipped else card_colors['question_bg']
            text_color = card_colors['text']
            label_color = card_colors['label']
            
            # Display content based on flip state
            if is_flipped:
                # BACK: Show facts
                display_text = "\n\n".join([f"• {fact}" for fact in card['facts']])
                card_side = "FACTS"
                emoji = "📋"
            else:
                # FRONT: Show title
                display_text = card['title']
                card_side = "TOPIC"
                emoji = card.get('emoji', '💡')
            
            button_key = f"flip_{idx}"
            
            # Generate image if on back and images enabled
            if is_flipped and make_pictures:
                if idx not in st.session_state.card_images:
                    with st.spinner(f"🎨 Generating image for card {idx + 1}..."):
                        image_prompt = card.get('image_prompt', f"Illustrate {card['title']}")
                        image, _ = generate_cartoon_from_reference(image_prompt, num_steps=image_quality)
                        st.session_state.card_images[idx] = image
            
            # Create card with optional image integration
            if is_flipped and make_pictures and idx in st.session_state.card_images:
                # Back of card with image - two column layout
                col_facts, col_image = st.columns([1.2, 1])
                
                with col_facts:
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, {bg_color} 0%, {bg_color}dd 100%);
                        padding: 50px 40px;
                        border-radius: 16px;
                        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
                        border: none;
                        transition: all 0.3s ease;
                        min-height: 350px;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        position: relative;
                        z-index: 1;
                    ">
                        <p style="
                            font-size: 12px;
                            color: {label_color} !important;
                            margin: 0 0 16px 0;
                            text-transform: uppercase;
                            letter-spacing: 3px;
                            font-weight: 800;
                        ">{card_side}</p>
                        <p style="
                            font-family: {st.session_state.font_style}, sans-serif;
                            font-size: {st.session_state.text_size}px;
                            color: {text_color} !important;
                            margin: 0;
                            letter-spacing: 0.3px;
                            word-spacing: 1.2px;
                            line-height: 1.7;
                            text-align: left;
                        ">{display_text}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_image:
                    st.image(
                        st.session_state.card_images[idx],
                        use_container_width=True
                    )
            else:
                # Front of card or back without images - centered layout
                st.markdown(f"""
                <div id="card-wrapper-{idx}" style="
                    position: relative;
                    margin: 28px 0;
                    width: 100%;
                ">
                    <div id="card-{idx}" style="
                        background: linear-gradient(135deg, {bg_color} 0%, {bg_color}dd 100%);
                        padding: 60px 50px;
                        border-radius: 16px;
                        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
                        border: none;
                        transition: all 0.3s ease;
                        min-height: 300px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        position: relative;
                        z-index: 1;
                    ">
                        <div style="text-align: center; width: 100%;">
                            <div style="
                                font-size: 80px;
                                margin-bottom: 28px;
                                display: inline-block;
                                line-height: 1;
                            ">{emoji}</div>
                            <p style="
                                font-size: 12px;
                                color: {label_color} !important;
                                margin: 0 0 20px 0;
                                text-transform: uppercase;
                                letter-spacing: 3px;
                                font-weight: 800;
                            ">{card_side}</p>
                            <p style="
                                font-family: {st.session_state.font_style}, sans-serif;
                                font-size: {max(st.session_state.text_size + 6, 24)}px;
                                color: {text_color} !important;
                                margin: 0;
                                letter-spacing: 0.3px;
                                word-spacing: 1.2px;
                                line-height: 1.8;
                                font-weight: {'700' if not is_flipped else '500'};
                            ">{display_text}</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Answer evaluation section (only on back of card)
            if is_flipped:
                # Initialize mnemonic cache
                if "card_mnemonics" not in st.session_state:
                    st.session_state.card_mnemonics = {}
                if "card_wacky_images" not in st.session_state:
                    st.session_state.card_wacky_images = {}
                
                # Generate mnemonic if not cached
                if idx not in st.session_state.card_mnemonics:
                    with st.spinner("🧠 Creating memory story..."):
                        from utils import generate_mnemonic, generate_wacky_image_from_concept
                        mnemonic = generate_mnemonic(card['title'], card['facts'])
                        st.session_state.card_mnemonics[idx] = mnemonic
                
                # Display mnemonic
                mnemonic_text = st.session_state.card_mnemonics.get(idx)
                if mnemonic_text:
                    st.markdown("---")
                    st.markdown(f"### 🧠 Memory Story")
                    st.info(f"**{mnemonic_text}**")
                
                # Generate wacky image if images enabled and not cached
                if make_pictures and idx not in st.session_state.card_wacky_images:
                    with st.spinner("🎨 Creating wild illustration..."):
                        from utils import generate_wacky_image_from_concept
                        wacky_img, wacky_prompt = generate_wacky_image_from_concept(
                            card['title'],
                            mnemonic_text,
                            num_steps=image_quality
                        )
                        if wacky_img:
                            st.session_state.card_wacky_images[idx] = wacky_img
                
                # Display wacky image
                if idx in st.session_state.card_wacky_images and make_pictures:
                    st.markdown("---")
                    st.markdown("### 🎨 Wacky Illustration")
                    st.image(
                        st.session_state.card_wacky_images[idx],
                        caption="(Wild & memorable!)",
                        use_container_width=True
                    )
                
                st.markdown("---")
                st.markdown("### 🎯 Try Answering")
                
                # Initialize answer storage
                if "card_answers" not in st.session_state:
                    st.session_state.card_answers = {}
                if "card_evaluations" not in st.session_state:
                    st.session_state.card_evaluations = {}
                
                # Get reference answer (first fact is the main answer)
                reference_answer = card['facts'][0] if card['facts'] else "No reference answer"
                
                # User's answer input
                user_input = st.text_area(
                    f"Your answer:",
                    value=st.session_state.card_answers.get(idx, ""),
                    height=80,
                    key=f"answer_{idx}",
                    placeholder="Type your answer here..."
                )
                
                # Store answer
                if user_input:
                    st.session_state.card_answers[idx] = user_input
                
                # Evaluate button
                eval_col1, eval_col2, eval_col3 = st.columns([1, 1.5, 1])
                with eval_col2:
                    if st.button("✅ Check Answer", key=f"evaluate_{idx}"):
                        if user_input.strip():
                            with st.spinner("🤖 Evaluating..."):
                                from utils import evaluate_answer_semantically
                                evaluation = evaluate_answer_semantically(
                                    user_input,
                                    reference_answer,
                                    card['title']
                                )
                                st.session_state.card_evaluations[idx] = evaluation
                        else:
                            st.warning("Please type an answer first!")
                
                # Show evaluation result
                if idx in st.session_state.card_evaluations:
                    eval_result = st.session_state.card_evaluations[idx]
                    
                    if eval_result.get("status") == "Correct":
                        st.success(f"✅ **Correct!** {eval_result.get('explanation', '')}")
                    elif eval_result.get("status") == "Partial":
                        st.info(f"⚠️ **Partial Credit.** {eval_result.get('explanation', '')}")
                    elif eval_result.get("status") == "Incorrect":
                        st.error(f"❌ **Not quite.** {eval_result.get('explanation', '')}")
                    else:
                        st.warning(f"Error: {eval_result.get('explanation', 'Unknown error')}")
            
            # Flip button
            button_col1, button_col2, button_col3 = st.columns([1, 1, 1])
            with button_col2:
                if st.button("Flip Card", key=button_key):
                    st.session_state.card_flipped[idx] = not st.session_state.card_flipped.get(idx, False)
                    st.rerun()
        
        # Study tools section
        st.markdown("""
        <style>
        .study-tools {{
            margin-top: 40px;
            padding-top: 28px;
            border-top: 2px solid rgba(255, 107, 107, 0.2);
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
