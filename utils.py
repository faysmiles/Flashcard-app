# utils.py - helper functions for the flashcard app

import streamlit as st
import re
import os
import requests
import json


# --- Wikipedia image search ---

@st.cache_data(show_spinner=False)
def search_wikipedia_image(query):
    """search wikipedia for a picture that matches the topic"""
    try:
        # clean up the query - remove emojis etc
        clean_query = re.sub(r'[^\w\s-]', '', query).strip()
        if not clean_query:
            return None
        
        search_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": clean_query,
            "gsrlimit": 5,  # get more results so we can pick the best one
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": 500,
        }
        
        response = requests.get(
            search_url, 
            params=params, 
            timeout=5,
            headers={"User-Agent": "FlashcardApp/1.0"}
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        
        # skip junk pages (disambiguation, lists, etc.)
        junk_keywords = ['disambiguation', 'list of', '(surname)', '(given name)']
        
        # try to find the best matching page (not just the first one with an image)
        query_words = set(clean_query.lower().split())
        best_match = None
        best_score = -1
        
        for page_id, page_data in pages.items():
            if "thumbnail" not in page_data:
                continue
            
            page_title = page_data.get("title", "").lower()
            
            # skip junk pages
            if any(junk in page_title for junk in junk_keywords):
                continue
            
            # score how well the page title matches our query
            title_words = set(page_title.split())
            overlap = len(query_words & title_words)
            
            # prefer pages where the title actually contains our search words
            if overlap > best_score:
                best_score = overlap
                best_match = page_data["thumbnail"]["source"]
        
        return best_match
    except Exception:
        return None


# --- card colours for different themes ---

def get_card_colors(colour_scheme):
    """return colours based on the selected theme"""
    color_map = {
        "Cream (Dyslexia Friendly)": {
            "card_bg": "#FFFEF9",
            "question_bg": "#FFF3E0",
            "text": "#3E2723",
            "accent": "#D4A574",
            "label": "#8B6914",
            "success": "#6B8E23",
            "flipped_bg": "#FFF3E0"
        },
        "Soft Blue": {
            "card_bg": "#FFFFFF",
            "question_bg": "#E3F2FD",
            "text": "#1A237E",
            "accent": "#3F51B5",
            "label": "#3A7CA5",
            "success": "#558B2F",
            "flipped_bg": "#E3F2FD"
        },
        "Light Grey": {
            "card_bg": "#FFFFFF",
            "question_bg": "#F5F5F5",
            "text": "#212121",
            "accent": "#757575",
            "label": "#616161",
            "success": "#558B2F",
            "flipped_bg": "#F5F5F5"
        },
        "Pale Lavender": {
            "card_bg": "#FFFFFF",
            "question_bg": "#F3E5F5",
            "text": "#4A148C",
            "accent": "#9C27B0",
            "label": "#7C3C9C",
            "success": "#6B8E23",
            "flipped_bg": "#F3E5F5"
        },
        "Pale Mint": {
            "card_bg": "#FFFFFF",
            "question_bg": "#E0F2F1",
            "text": "#1B5E20",
            "accent": "#4CAF50",
            "label": "#3C8C6C",
            "success": "#6B8E23",
            "flipped_bg": "#E0F2F1"
        }
    }
    return color_map.get(colour_scheme, color_map["Cream (Dyslexia Friendly)"])


# --- emoji matching ---

def get_emoji_for_topic(text):
    """pick an emoji based on what the topic is about"""
    text_lower = text.lower()
    
    emoji_map = {
        'moon|planet|star|space|orbit|gravity|solar': '🌙',
        'atom|molecule|element|chemical|reaction': '⚛️',
        'cell|biology|organism|gene|dna': '🧬',
        'energy|power|electricity|light': '⚡',
        'earth|geology|rock|mineral': '🪨',
        'water|ocean|sea|liquid': '💧',
        'weather|climate|temperature|wind': '🌤️',
        'ecosystem|nature|forest|animal|plant': '🌿',
        'anatomy|body|heart|brain|human': '🫀',
        'number|math|calculate|equation': '🔢',
        'history|ancient|war|battle|empire': '⚔️',
        'art|painting|sculpture|creative': '🎨',
        'music|song|instrument': '🎵',
        'literature|book|story|author': '📚',
        'country|city|continent|map': '🗺️',
        'mountain|hill|valley': '⛰️',
        'computer|technology|software|code': '💻',
        'internet|network|server': '🌐',
        'robot|machine|artificial': '🤖',
        'disease|medicine|doctor|health': '⚕️',
        'exercise|fitness|sport': '💪',
        'food|nutrition|diet': '🍎',
        'economy|money|trade|business': '💰',
        'government|law|politics': '⚖️',
        'education|school|learn|teach': '🎓',
        'elephant|tiger|lion|whale|dolphin|bird': '🐘',
    }
    
    for keywords, emoji in emoji_map.items():
        for keyword in keywords.split('|'):
            if keyword in text_lower:
                return emoji
    
    return '💡'  # default


# --- LLM flashcard generation (this is the main one) ---

def generate_flashcards_from_llm(raw_text, reading_level="intermediate"):
    """send text to claude and get flashcards back"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("Can't find the AI key - please check your settings.")
        return None
    
    # set up the reading level instructions
    if reading_level == "simple":
        level_instructions = """READING LEVEL: EASY (Ages 4-11)
- Use very simple words only, like a children's book
- Short sentences (8-12 words max per fact)
- No big or technical words
- Titles should be 2-4 simple words
- Make it friendly and fun"""
    elif reading_level == "complex":
        level_instructions = """READING LEVEL: ADVANCED (Ages 18+)
- Use precise academic language
- Include technical terms and proper terminology
- Facts can be longer and more detailed (up to 25 words)
- Maintain accuracy and depth"""
    else:
        level_instructions = """READING LEVEL: MEDIUM (Ages 11-18)
- Use clear everyday language a teenager would understand
- Medium sentences (12-18 words per fact)
- Explain technical terms briefly when used"""
    
    prompt = f"""You are creating flashcards for a student. Follow the reading level requirements EXACTLY.

{level_instructions}

TEXT TO CONVERT:
{raw_text}

Return ONLY a valid JSON array in this exact format (no preamble, no explanation, just JSON):
[
  {{
    "title": "Brief title/topic",
    "facts": ["Fact 1", "Fact 2", "Fact 3"],
    "topic_keyword": "main keyword for emoji matching",
    "image_search": "specific search term to find a relevant wikipedia image (be precise, e.g. 'African elephant' not just 'elephant')"
  }}
]

Rules:
- Create 3-5 flashcards
- Each card has 1-3 facts
- Facts MUST match the reading level above
- image_search should be a specific noun or phrase that would find the right picture on wikipedia"""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30
        )
        
        if response.status_code != 200:
            st.error("Something went wrong talking to the AI - please try again in a moment.")
            return None
        
        # get the text out of the response
        api_response = response.json()
        text_content = api_response["content"][0]["text"].strip()
        
        # clean up markdown code blocks if claude added them
        if text_content.startswith("```json"):
            text_content = text_content[7:]
        if text_content.startswith("```"):
            text_content = text_content[3:]
        if text_content.endswith("```"):
            text_content = text_content[:-3]
        text_content = text_content.strip()
        
        # turn the json into flashcard dicts
        flashcard_data = json.loads(text_content)
        
        flashcards = []
        for card in flashcard_data:
            emoji = get_emoji_for_topic(card.get("topic_keyword", card["title"]))
            flashcards.append({
                'title': card['title'],
                'facts': card['facts'],
                'emoji': emoji,
                'image_search': card.get('image_search', card['title']),
            })
        
        return flashcards
    
    except json.JSONDecodeError:
        st.error("The AI's reply didn't come back in the right format - please try again.")
        return None
    except requests.exceptions.RequestException:
        st.error("Couldn't reach the AI - please check your internet and try again.")
        return None
    except Exception:
        st.error("Something went wrong - please try again.")
        return None


# --- file text extraction ---

def extract_text_from_file(uploaded_file):
    """pull text out of uploaded pdf, docx, or txt files"""
    try:
        if uploaded_file.type == "text/plain":
            return uploaded_file.read().decode('utf-8')
        
        elif uploaded_file.type == "application/pdf":
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            from docx import Document
            doc = Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
        
        else:
            return "Not supported - please use PDF, DOCX, or TXT."
    
    except Exception:
        return "Sorry, couldn't read that file - please try a different one."


# --- CSS styling ---

def apply_styles(font_style, text_size, colour_scheme):
    """apply the dyslexia-friendly styles to the page"""
    
    colors = {
        "Cream (Dyslexia Friendly)": {"bg": "#F5F1E8", "text": "#2C2416", "accent": "#8B6914"},
        "Soft Blue": {"bg": "#E8F1F5", "text": "#1C3A42", "accent": "#3A7CA5"},
        "Light Grey": {"bg": "#F1F1F1", "text": "#2C2C2C", "accent": "#666666"},
        "Pale Lavender": {"bg": "#F5E8F5", "text": "#3C2C42", "accent": "#7C3C9C"},
        "Pale Mint": {"bg": "#E8F5F1", "text": "#1C3C32", "accent": "#3C8C6C"},
    }
    
    c = colors.get(colour_scheme, colors["Cream (Dyslexia Friendly)"])
    
    # we use css variables so we only inject the theme values once at the top
    # then the rest of the css just references them with var(--name)
    st.markdown(f"""
    <style>
    :root {{
        --bg: {c['bg']};
        --text: {c['text']};
        --accent: {c['accent']};
        --font-family: {font_style};
        --font-size: {text_size}px;
    }}
    
    [data-testid="stAppViewContainer"] {{ background-color: var(--bg) !important; }}
    [data-testid="stMainBlockContainer"] {{ background-color: var(--bg) !important; }}
    section[data-testid="stSidebar"] {{ background-color: var(--bg) !important; }}
    [data-testid="stColumn"] {{ background-color: var(--bg) !important; }}
    
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stMarkdownContainer"] li {{
        font-family: var(--font-family), sans-serif !important;
        font-size: var(--font-size) !important;
        color: var(--text) !important;
        letter-spacing: 0.35px !important;
        word-spacing: 1.23px !important;
        line-height: 1.8 !important;
    }}
    
    h1, h2, h3, h4, h5, h6 {{
        font-family: var(--font-family), sans-serif !important;
        color: var(--accent) !important;
        font-weight: 700 !important;
    }}
    
    label {{
        font-family: var(--font-family), sans-serif !important;
        font-size: var(--font-size) !important;
        color: var(--text) !important;
        background-color: transparent !important;
    }}
    
    [data-testid="stSelectbox"] div div {{
        background-color: #FFFFFF !important;
        color: var(--text) !important;
    }}
    
    [data-testid="stTextArea"] textarea {{
        background-color: #FFFFFF !important;
        color: var(--text) !important;
        font-family: var(--font-family), sans-serif !important;
        font-size: var(--font-size) !important;
    }}
    
    [data-testid="stRadio"] label {{ background-color: transparent !important; }}
    [data-testid="stCheckbox"] label {{ background-color: transparent !important; }}
    
    button {{
        font-family: var(--font-family), sans-serif !important;
        font-size: var(--font-size) !important;
    }}
    
    button:hover {{ background-color: rgba(0, 0, 0, 0.05) !important; }}
    i, em {{ font-style: normal !important; }}
    hr {{ border-color: var(--accent) !important; }}
    </style>
    """, unsafe_allow_html=True)
