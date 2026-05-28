# utils.py - COMPLETELY FIXED (Emojis + Images + Wikipedia)
import streamlit as st
import re
import os
import requests
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

# ==================== EMOJI FIX - PROPER DOG EMOJI ====================

def get_emoji_for_topic(text):
    """Get correct emoji based on topic - FIXED for dogs!"""
    text_lower = text.lower()
    
    # Specific animal mappings
    animal_map = {
        'dog': '🐕', 'dogs': '🐕', 'puppy': '🐕', 'puppies': '🐕', 'canine': '🐕',
        'cat': '🐈', 'cats': '🐈', 'kitten': '🐈', 'feline': '🐈',
        'lion': '🦁', 'lioness': '🦁', 'tiger': '🐅', 'tiger cub': '🐅',
        'elephant': '🐘', 'elephants': '🐘',
        'giraffe': '🦒', 'giraffes': '🦒',
        'whale': '🐋', 'whales': '🐋', 'dolphin': '🐬', 'dolphins': '🐬',
        'bird': '🐦', 'birds': '🐦', 'eagle': '🦅', 'owl': '🦉',
        'butterfly': '🦋', 'butterflies': '🦋',
        'bee': '🐝', 'bees': '🐝',
        'fish': '🐟', 'fishes': '🐟', 'shark': '🦈',
        'snake': '🐍', 'snakes': '🐍',
        'frog': '🐸', 'frogs': '🐸',
        'rabbit': '🐰', 'rabbits': '🐰', 'bunny': '🐰',
        'horse': '🐴', 'horses': '🐴', 'pony': '🐴',
        'cow': '🐄', 'cows': '🐄', 'bull': '🐂',
        'pig': '🐷', 'pigs': '🐷',
        'sheep': '🐑', 'lambs': '🐑',
        'goat': '🐐', 'goats': '🐐',
        'monkey': '🐒', 'monkeys': '🐒', 'ape': '🦍',
        'bear': '🐻', 'bears': '🐻', 'polar bear': '🐻‍❄️',
        'panda': '🐼', 'pandas': '🐼',
        'kangaroo': '🦘', 'koala': '🐨',
        'fox': '🦊', 'deer': '🦌', 'moose': '🦌',
        'zebra': '🦓', 'hippo': '🦛', 'rhino': '🦏',
    }
    
    # Check for animal keywords
    for keyword, emoji in animal_map.items():
        if keyword in text_lower:
            return emoji
    
    # Science and nature
    science_map = {
        'moon': '🌙', 'planet': '🪐', 'star': '⭐', 'sun': '☀️',
        'atom': '⚛️', 'molecule': '🧪', 'dna': '🧬', 'cell': '🔬',
        'brain': '🧠', 'heart': '❤️', 'bone': '🦴',
        'tree': '🌳', 'flower': '🌸', 'leaf': '🌿', 'plant': '🌱',
        'mountain': '⛰️', 'volcano': '🌋', 'ocean': '🌊', 'river': '🏞️',
        'rain': '🌧️', 'snow': '❄️', 'lightning': '⚡',
    }
    
    for keyword, emoji in science_map.items():
        if keyword in text_lower:
            return emoji
    
    # Default emojis by first letter (fun fallback)
    letter_emoji = {
        'a': '🅰️', 'b': '🅱️', 'c': '©️', 'd': '🐕', 'e': '📧',
        'f': '🎏', 'g': '🅶', 'h': '♓', 'i': 'ℹ️', 'j': '🇯',
        'k': '🇰', 'l': '🇱', 'm': 'Ⓜ️', 'n': '🇳', 'o': '🅾️',
        'p': '🅿️', 'q': '🇶', 'r': '🇷', 's': '💲', 't': '🌮',
        'u': '🇺', 'v': '🇻', 'w': '🇼', 'x': '❌', 'y': '🇾', 'z': '🇿'
    }
    
    first_char = text_lower[0] if text_lower else ''
    return letter_emoji.get(first_char, '📚')


# ==================== BETTER IMAGE SEARCH WITH WIKIPEDIA BACKUP ====================

@st.cache_data(show_spinner=False, ttl=3600)
def search_wikipedia_image(query):
    """Search Wikipedia for images - MULTIPLE FALLBACKS"""
    if not query:
        return None
    
    clean_query = re.sub(r'[^\w\s-]', '', query).strip()
    if not clean_query:
        return None
    
    # List of API endpoints to try (multiple fallbacks)
    search_terms = [
        clean_query,
        clean_query.split()[0] if len(clean_query.split()) > 1 else clean_query,
        clean_query + " species" if "dog" in clean_query.lower() or "cat" in clean_query.lower() else clean_query,
    ]
    
    for term in search_terms[:3]:  # Try up to 3 variations
        try:
            # Try direct page first
            params = {
                "action": "query",
                "format": "json",
                "titles": term,
                "prop": "pageimages",
                "piprop": "thumbnail",
                "pithumbsize": 500,
            }
            
            response = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params=params,
                timeout=8,
                headers={"User-Agent": "FlashcardMagic/1.0 (educational; contact@example.com)"}
            )
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    if "thumbnail" in page_data and int(page_id) > 0:
                        img_url = page_data["thumbnail"]["source"]
                        if img_url and not any(x in page_data.get("title", "").lower() for x in ['disambiguation', 'list of']):
                            return img_url
            
            # Try search if direct failed
            params = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": term,
                "gsrlimit": 10,
                "prop": "pageimages",
                "piprop": "thumbnail",
                "pithumbsize": 500,
            }
            
            response = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params=params,
                timeout=8,
                headers={"User-Agent": "FlashcardMagic/1.0"}
            )
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get("query", {}).get("pages", {})
                
                # Sort by relevance (page ID positive)
                valid_pages = []
                for page_id, page_data in pages.items():
                    if "thumbnail" in page_data and int(page_id) > 0:
                        title = page_data.get("title", "").lower()
                        # Skip disambiguation pages
                        if not any(bad in title for bad in ['disambiguation', 'list of', '(disambiguation)']):
                            valid_pages.append(page_data)
                
                # Return the best match (first one)
                for page_data in valid_pages:
                    if "thumbnail" in page_data:
                        return page_data["thumbnail"]["source"]
        
        except Exception as e:
            print(f"Wikipedia search error for '{term}': {str(e)}")
            continue
    
    # Special fallback for common animals - use direct known image URLs
    animal_fallbacks = {
        'dog': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Golden_Retriever_Dukedog_Clipping.jpg/500px-Golden_Retriever_Dukedog_Clipping.jpg',
        'cat': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/500px-Cat03.jpg',
        'lion': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Lion_waiting_in_Namibia.jpg/500px-Lion_waiting_in_Namibia.jpg',
        'elephant': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/bf/African_Bush_Elephant.jpg/500px-African_Bush_Elephant.jpg',
        'giraffe': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Giraffe_Mikumi_National_Park.jpg/500px-Giraffe_Mikumi_National_Park.jpg',
        'butterfly': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Monarch_Butterfly_Danaus_plexippus.jpg/500px-Monarch_Butterfly_Danaus_plexippus.jpg',
    }
    
    for key, url in animal_fallbacks.items():
        if key in clean_query.lower():
            return url
    
    return None


# ==================== DEEPSEEK FLASHCARD GENERATION ====================

@st.cache_data(show_spinner=False, ttl=3600)
def generate_flashcards_from_llm(raw_text, reading_level="intermediate"):
    """Generate flashcards using DeepSeek API"""
    
    # Get DeepSeek API key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["DEEPSEEK_API_KEY"]
        except:
            st.error("🔑 Missing DeepSeek API key")
            st.info("Add your key to .env or Streamlit secrets")
            return None
    
    # Scale card count
    n_chars = len(raw_text)
    if n_chars <= 8000:
        min_cards, max_cards = 3, 5
    elif n_chars <= 16000:
        min_cards, max_cards = 5, 8
    else:
        min_cards, max_cards = 8, 12
    
    # Reading level instructions
    if reading_level == "simple":
        level_text = "VERY SIMPLE: Use short words, short sentences (8-12 words max)"
    elif reading_level == "complex":
        level_text = "ADVANCED: Use precise academic language, longer sentences (up to 25 words)"
    else:
        level_text = "MEDIUM: Clear everyday language, medium sentences (12-18 words)"
    
    prompt = f"""Create {min_cards}-{max_cards} flashcards from this text.

READING LEVEL: {level_text}

IMPORTANT RULES:
- For dog-related content, use 🐕 emoji (NOT 🦁)
- For cat-related content, use 🐈 emoji
- Each fact should have a RELEVANT emoji that matches the content
- Return ONLY valid JSON

Example format:
{{
  "flashcards": [
    {{
      "title": "Dogs as Pets",
      "topic_keyword": "dog",
      "image_search": "dog",
      "facts": [
        {{"text": "There are 700 million to 1 billion dogs worldwide.", "emoji_hint": "dog"}},
        {{"text": "Dogs are the most popular pet in the US.", "emoji_hint": "dog"}}
      ]
    }}
  ]
}}

TEXT:
{raw_text[:15000]}"""

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You create flashcards. Use correct emojis (🐕 for dogs, not 🦁). Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        # Parse response
        content = response.choices[0].message.content
        # Clean up any markdown code blocks
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        
        result = json.loads(content)
        flashcard_data = result.get("flashcards", [])
        
        if not flashcard_data:
            st.error("No flashcards generated")
            return None
        
        # Process flashcards with correct emojis
        flashcards = []
        for card in flashcard_data:
            topic = card.get("title", "")
            topic_keyword = card.get("topic_keyword", topic)
            topic_emoji = get_emoji_for_topic(topic_keyword or topic)
            
            facts = []
            for fact in card.get("facts", [])[:4]:  # Max 4 facts per card
                if isinstance(fact, dict):
                    fact_text = fact.get("text", "")
                    emoji_hint = fact.get("emoji_hint", fact_text[:20])
                    fact_emoji = get_emoji_for_topic(emoji_hint)
                    facts.append({"emoji": fact_emoji, "text": fact_text})
                elif isinstance(fact, str):
                    facts.append({"emoji": topic_emoji, "text": fact})
            
            flashcards.append({
                'title': topic,
                'facts': facts,
                'emoji': topic_emoji,
                'image_search': card.get('image_search', topic_keyword),
            })
        
        return flashcards
    
    except json.JSONDecodeError as e:
        st.error(f"JSON parsing error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"API error: {str(e)}")
        return None


# ==================== EXISTING HELPER FUNCTIONS (keep these) ====================

def get_card_colors(colour_scheme):
    color_map = {
        "Soft Blue": {"text": "#1A237E", "label": "#3A7CA5", "accent": "#3F51B5"},
        "Pale Lavender": {"text": "#4A148C", "label": "#7C3C9C", "accent": "#9C27B0"},
        "Pale Mint": {"text": "#1B5E20", "label": "#2F7A55", "accent": "#4CAF50"},
        "Low Stimulation": {"text": "#2E2E2E", "label": "#555555", "accent": "#7A7A7A"},
    }
    return color_map.get(colour_scheme, color_map["Low Stimulation"])


def extract_text_from_file(uploaded_file):
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
        elif "wordprocessingml" in uploaded_file.type:
            from docx import Document
            doc = Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
        else:
            return "Unsupported file type"
    except Exception as e:
        return f"Error: {str(e)}"


def fetch_image_bytes(url):
    if not url:
        return None
    try:
        r = requests.get(url, headers={"User-Agent": "FlashcardMagic/1.0"}, timeout=10)
        if r.ok:
            return r.content
    except:
        pass
    return None


def render_card_to_png(card, colors, idx, total, wiki_image_bytes=None, page_bg_hex="#F5F1E8"):
    """Simple PNG render"""
    W = 700
    MARGIN = 30
    
    img = Image.new("RGB", (W, 500), page_bg_hex)
    draw = ImageDraw.Draw(img)
    
    # Card background
    draw.rectangle([MARGIN, MARGIN, W-MARGIN, 470], fill="#FFFFFF", outline=colors['accent'], width=3)
    
    # Title
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 18)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Center title
    bbox = draw.textbbox((0, 0), card['title'], font=font)
    text_width = bbox[2] - bbox[0]
    draw.text(((W - text_width) // 2, 100), card['title'], fill=colors['text'], font=font)
    
    # Draw facts
    y = 180
    for fact in card['facts'][:3]:
        text = fact.get('text', '')[:100]
        emoji = fact.get('emoji', '•')
        draw.text((MARGIN + 20, y), f"{emoji} {text}", fill=colors['text'], font=small_font)
        y += 45
    
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def build_cards_zip(flashcards, card_images, colors, page_bg_hex, cache_key):
    import zipfile
    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, card in enumerate(flashcards[:10]):
            img_bytes = fetch_image_bytes(card_images.get(i))
            png = render_card_to_png(card, colors, i, len(flashcards), img_bytes, page_bg_hex)
            safe_title = re.sub(r'[^a-zA-Z0-9_-]+', '_', card['title'])[:30]
            zf.writestr(f"card_{i+1}_{safe_title}.png", png)
    return zip_buf.getvalue()


def render_header(app_title, app_subtitle, text_size, colour_scheme):
    st.markdown(f"""
    <div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #2C5282, #3182CE); border-radius: 12px; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0; font-size: {text_size * 2}px;'>💡 {app_title}</h1>
        <p style='color: rgba(255,255,255,0.9); margin: 10px 0 0 0;'>{app_subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def render_feedback_box(feedback_url, colour_scheme):
    st.markdown(f"""
    <div style='text-align: center; padding: 20px; margin-top: 40px; border-top: 1px solid #ddd;'>
        <p>💬 Help improve this app! <a href='{feedback_url}' target='_blank'>Take Survey</a></p>
    </div>
    """, unsafe_allow_html=True)


def render_mobile_settings_hint():
    st.markdown("""
    <div style='background: #f0f0f0; padding: 10px; border-radius: 8px; margin-bottom: 15px; text-align: center; font-size: 14px;'>
        ⚙️ Tap the <strong>☰</strong> icon in the top-left to access settings!
    </div>
    """, unsafe_allow_html=True)


def apply_styles(font_style, text_size, colour_scheme, line_spacing=1.8):
    st.markdown(f"""
    <style>
    * {{
        font-family: '{font_style}', sans-serif !important;
    }}
    p, li, label {{
        font-size: {text_size}px !important;
        line-height: {line_spacing} !important;
    }}
    .stButton button {{
        border-radius: 10px !important;
        padding: 10px 20px !important;
        font-weight: bold !important;
    }}
    </style>
    """, unsafe_allow_html=True)
