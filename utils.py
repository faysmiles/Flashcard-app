# utils.py — Core functions for summarisation, image generation, and styling

import streamlit as st
from transformers import BartForConditionalGeneration, BartTokenizer
from diffusers import StableDiffusionPipeline
import torch
import re
import os
import requests
from config import SUMMARIZATION_MODEL, IMAGE_MODEL

# ==================== WIKIPEDIA IMAGE SEARCH (FREE, NO API KEY) ====================

def search_wikipedia_image(query):
    """
    Search Wikipedia for a relevant image for a topic.
    This is FAST, FREE, and requires NO API KEY.
    
    Args:
        query: The topic/title to search for (e.g., "Moon phases")
    
    Returns:
        URL of the image, or None if not found
    """
    try:
        # Clean up the query - remove emojis and extra chars
        clean_query = re.sub(r'[^\w\s-]', '', query).strip()
        if not clean_query:
            return None
        
        # Wikipedia API - search for matching article with image
        search_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": clean_query,
            "gsrlimit": 3,
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
        
        # Find first page with a thumbnail image
        for page_id, page_data in pages.items():
            if "thumbnail" in page_data and "source" in page_data["thumbnail"]:
                return page_data["thumbnail"]["source"]
        
        return None
    except Exception:
        return None

# ==================== DYSLEXIA-FRIENDLY CARD COLORS ====================

def get_card_colors(colour_scheme):
    """
    Return dyslexia-friendly card colors based on the selected background scheme.
    Both question and answer sides use the same background color for visual consistency.
    
    Args:
        colour_scheme: The selected colour scheme name
    
    Returns:
        Dict with 'bg', 'text', 'accent', 'success', 'label' colors
    """
    color_map = {
        "Cream (Dyslexia Friendly)": {
            "card_bg": "#FFFEF9",           # Warm white
            "question_bg": "#FFF3E0",       # Soft peach (warm)
            "text": "#3E2723",              # Dark brown
            "accent": "#D4A574",            # Warm gold
            "label": "#8B6914",             # Warm accent
            "success": "#6B8E23",           # Sage green
            "flipped_bg": "#FFF3E0"         # Same as question (peach)
        },
        "Soft Blue": {
            "card_bg": "#FFFFFF",           # Clean white
            "question_bg": "#E3F2FD",       # Light soft blue
            "text": "#1A237E",              # Deep navy
            "accent": "#3F51B5",            # Soft indigo
            "label": "#3A7CA5",             # Blue accent
            "success": "#558B2F",           # Muted green
            "flipped_bg": "#E3F2FD"         # Same as question (light blue)
        },
        "Light Grey": {
            "card_bg": "#FFFFFF",           # Pure white (neutral)
            "question_bg": "#F5F5F5",       # Very light grey (neutral)
            "text": "#212121",              # Dark anthracite
            "accent": "#757575",            # Medium grey
            "label": "#616161",             # Neutral grey
            "success": "#558B2F",           # Muted green
            "flipped_bg": "#F5F5F5"         # Same as question (light grey)
        },
        "Pale Lavender": {
            "card_bg": "#FFFFFF",           # Clean white
            "question_bg": "#F3E5F5",       # Very pale lavender
            "text": "#4A148C",              # Deep plum
            "accent": "#9C27B0",            # Soft purple
            "label": "#7C3C9C",             # Purple accent
            "success": "#6B8E23",           # Sage green
            "flipped_bg": "#F3E5F5"         # Same as question (pale lavender)
        },
        "Pale Mint": {
            "card_bg": "#FFFFFF",           # Clean white
            "question_bg": "#E0F2F1",       # Pale mint/cyan
            "text": "#1B5E20",              # Dark forest green
            "accent": "#4CAF50",            # Muted green
            "label": "#3C8C6C",             # Green accent
            "success": "#6B8E23",           # Sage green
            "flipped_bg": "#E0F2F1"         # Same as question (pale mint)
        }
    }
    
    return color_map.get(colour_scheme, color_map["Cream (Dyslexia Friendly)"])

# ==================== TOPIC & EMOJI DETECTION ====================

def get_topic_emoji_mapping():
    """
    Map common topics to relevant emojis for flashcards.
    Uses keywords to identify subject matter.
    """
    return {
        # Science
        'moon|planet|star|space|orbit|gravity|solar': '🌙',
        'atom|molecule|element|chemical|reaction': '⚛️',
        'cell|biology|organism|gene|dna': '🧬',
        'energy|power|electricity|light': '⚡',
        'earth|geology|rock|mineral': '🪨',
        'water|ocean|sea|liquid': '💧',
        'weather|climate|temperature|wind': '🌤️',
        'ecosystem|nature|forest|animal|plant': '🌿',
        'anatomy|body|heart|brain|human': '🫀',
        
        # Math & Numbers
        'number|math|calculate|equation|algebra|geometry': '🔢',
        'data|graph|chart|statistics': '📊',
        
        # History & Culture
        'history|ancient|war|battle|empire': '⚔️',
        'culture|tradition|festival|celebration': '🎉',
        'art|painting|sculpture|creative': '🎨',
        'music|song|instrument|rhythm': '🎵',
        'literature|book|story|author|poem': '📚',
        
        # Geography
        'country|city|continent|map|location': '🗺️',
        'mountain|hill|valley|landscape': '⛰️',
        
        # Technology
        'computer|technology|software|digital|code': '💻',
        'internet|network|data|server': '🌐',
        'robot|machine|automation|artificial': '🤖',
        
        # Health & Medicine
        'disease|medicine|doctor|hospital|health': '⚕️',
        'exercise|fitness|sport|athlete': '💪',
        'food|nutrition|diet|meal': '🍎',
        
        # Economics & Society
        'economy|money|trade|business': '💰',
        'government|law|politics|rule': '⚖️',
        'education|school|learn|teach': '🎓',
        
        # General fallback
        'question|idea|concept|topic|subject': '💡',
    }

def identify_topic(text):
    """
    Identify the main topic from flashcard text.
    Returns the topic keyword and appropriate emoji.
    
    Args:
        text: The flashcard text (question or answer)
    
    Returns:
        Tuple: (topic, emoji)
    """
    text_lower = text.lower()
    emoji_map = get_topic_emoji_mapping()
    
    # Check for matching topics
    for keywords, emoji in emoji_map.items():
        for keyword in keywords.split('|'):
            if keyword in text_lower:
                return (keyword, emoji)
    
    # Default fallback
    return ('concept', '💡')

# ==================== IMPROVED Q&A GENERATION ====================

def generate_smart_question(fact, index=1):
    """
    Generate a clear, engaging question that properly matches the answer.
    Uses 15+ sophisticated patterns to create varied, natural-sounding questions.
    
    Args:
        fact: The fact/statement text (will be the answer)
        index: Card number
    
    Returns:
        Clear, engaging, relevant question string
    """
    fact = fact.strip()
    fact_lower = fact.lower()
    
    # Pattern 1: Definitional - "X is Y / X are Y"
    if re.match(r'^([A-Za-z\s]+)\s+(?:is|are|was|were)\s+', fact):
        match = re.match(r'^([A-Za-z\s]+)\s+(?:is|are|was|were)\s+', fact)
        if match:
            subject = match.group(1).strip()
            return f"What is {subject}?"
        return "What does this term mean?"
    
    # Pattern 2: Compositional - "X has/contains/consists of Y"
    if re.search(r'\b(has|have|contains?|includes?|consists of|made of|comprised of|composed of)\b', fact_lower):
        match = re.search(r'^([A-Za-z\s]+)\s+(?:has|have|contains?|includes?|consists of|made of)', fact)
        if match:
            subject = match.group(1).strip()
            return f"What does {subject} consist of?"
        return "What are the component parts?"
    
    # Pattern 3: Causal - "X causes/results in/leads to Y"
    if re.search(r'\b(cause|causes|caused|result|results in|lead|leads to|trigger|triggers|produce|produces|due to)\b', fact_lower):
        if re.search(r'causes?|results? in|leads? to', fact_lower):
            match = re.search(r'([A-Za-z\s]+)\s+(?:causes?|results? in|leads? to)', fact)
            if match:
                subject = match.group(1).strip()
                return f"What effect does {subject} have?"
        return "What are the causes or effects?"
    
    # Pattern 4: Functional - "X helps/enables/allows/supports Y"
    if re.search(r'\b(helps?|allows?|enables?|supports?|facilitates?|assists?|aids?)\b', fact_lower):
        match = re.search(r'^([A-Za-z\s]+)\s+(?:helps?|allows?|enables?|supports?)', fact)
        if match:
            subject = match.group(1).strip()
            return f"How does {subject} help or contribute?"
        return "What is the purpose or function?"
    
    # Pattern 5: Temporal - "X happens when Y / X occurs during Y"
    if re.search(r'\b(when|during|after|before|while|as)\b', fact_lower):
        if 'when' in fact_lower or 'during' in fact_lower:
            match = re.search(r'^([A-Za-z\s]+)\s+(?:happens?|occurs?)', fact)
            if match:
                subject = match.group(1).strip()
                return f"When does {subject} occur?"
            return "Under what circumstances or timing?"
    
    # Pattern 6: Categorical - "Types/kinds/categories of X"
    if re.search(r'\b(types?|kinds?|categories?|forms?|species|varieties?|variations?|subtypes?)\b', fact_lower):
        match = re.search(r'(?:types?|kinds?|categories?|forms?|species|varieties?|variations?)\s+(?:of\s+)?([A-Za-z\s]+)', fact)
        if match:
            subject = match.group(1).strip()
            return f"What are the main types or categories of {subject}?"
        return "What different kinds exist?"
    
    # Pattern 7: Capability - "X can/may/could/might do Y"
    if re.search(r'\b(can|may|might|could|able to|capable of)\b', fact_lower):
        match = re.search(r'^([A-Za-z\s]+)\s+(?:can|may|might|could)', fact)
        if match:
            subject = match.group(1).strip()
            return f"What capabilities does {subject} have?"
        return "What is possible or capable?"
    
    # Pattern 8: Discovery/Innovation - "X was discovered/found/created/invented/developed"
    if re.search(r'\b(discover|found|created|invented|developed|introduced|designed|made|built)\b', fact_lower):
        match = re.search(r'(?:discover|found|created|invented|developed|introduced|designed)\s+(?:by\s+)?([A-Za-z\s]+)', fact)
        if match:
            return "How was this discovered or created?"
        return "What important discovery or invention is this?"
    
    # Pattern 9: Importance/Significance - "X is important/crucial/essential/significant"
    if re.search(r'\b(important|significant|essential|crucial|vital|critical|fundamental|key)\b', fact_lower):
        match = re.search(r'^([A-Za-z\s]+)\s+is\s+(?:important|significant|essential)', fact)
        if match:
            subject = match.group(1).strip()
            return f"Why is {subject} important or significant?"
        return "What makes this significant?"
    
    # Pattern 10: Comparative - "X is larger/smaller/greater/less than Y"
    if re.search(r'\b(larger?|smaller?|greater?|less|more|bigger?|longer?|shorter?|higher?|lower?|older?|younger?)\b', fact_lower):
        match = re.search(r'([A-Za-z\s]+)\s+is\s+(?:larger?|greater?|more|bigger?)', fact)
        if match:
            subject = match.group(1).strip()
            return f"How does {subject} compare in size or scale?"
        return "What is the comparison or relationship?"
    
    # Pattern 11: Characteristic/Attribute - "X is [adjective] with [properties]"
    if re.search(r'diameter|size|color|shape|temperature|length|height|weight|speed', fact_lower):
        return "What are the key characteristics or properties?"
    
    # Pattern 12: Process/Sequence - "X happens in steps / First... then... finally..."
    if re.search(r'\b(first|then|next|finally|step|stage|phase|process|sequence|cycle|procedure)\b', fact_lower):
        return "What is the sequence or process?"
    
    # Pattern 13: Relationship - "X relates to/affects/influences Y"
    if re.search(r'\b(relates to|affects?|influences?|impacts?|connects to|associated with|linked to)\b', fact_lower):
        match = re.search(r'([A-Za-z\s]+)\s+(?:relates to|affects?|influences?|impacts?)', fact)
        if match:
            subject = match.group(1).strip()
            return f"How does {subject} relate to other concepts?"
        return "What are the relationships or connections?"
    
    # Pattern 14: Quantitative - "X is [number] [units]"
    if re.search(r'(\d+(?:\.\d+)?)\s+(km|meters?|miles?|years?|days?|hours?|percent?|%)', fact_lower):
        return "What are the important measurements or quantities?"
    
    # Pattern 15: Descriptive narrative - Long descriptive sentences
    if len(fact) > 100:
        # Extract first key concept
        words = fact.split()
        key_words = [w for w in words if len(w) > 4 and w[0].isupper()]
        if key_words:
            return f"Describe the key features of {key_words[0].lower()}."
        return "What is described in this passage?"
    
    # Fallback: Generic but appropriate
    words = fact.split()
    if len(words) > 3:
        return f"Explain the main points about: {fact[:40]}{'...' if len(fact) > 40 else ''}"
    
    return "What does this concept mean?"

# ==================== MNEMONICS & WACKY IMAGES ====================

def generate_mnemonic(concept, facts):
    """
    Generate a memorable, wacky mnemonic/story for a concept.
    Makes it intentionally vivid and unusual so it sticks in memory.
    
    Args:
        concept: The card title/topic
        facts: List of facts to remember
    
    Returns:
        String with the mnemonic story, or None if error
    """
    import requests
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    
    facts_str = " ".join(facts[:2])  # Use first 2 facts
    
    prompt = f"""Create a MEMORABLE, WACKY, FUNNY mnemonic or story for this concept.

Concept: {concept}
Key facts: {facts_str}

Make it vivid, unusual, and deliberately weird so it STICKS in memory. Use exaggeration, 
funny imagery, or unexpected comparisons. 2-3 sentences max. Be creative and zany!

Example format: "Picture a giant [CRAZY VISUAL] doing [WEIRD ACTION] with [OBJECT]..."
"""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 150,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
            },
            timeout=10
        )
        
        if response.status_code == 200:
            api_response = response.json()
            mnemonic = api_response["content"][0]["text"].strip()
            return mnemonic
        return None
    except:
        return None

def generate_wacky_image_from_concept(concept, mnemonic=None, num_steps=30):
    """
    Generate a wild, memorable illustration for a concept.
    Uses creative prompt engineering to make it deliberately zany.
    
    Args:
        concept: The concept to illustrate
        mnemonic: Optional mnemonic to incorporate
        num_steps: Diffusion steps (higher = better but slower)
    
    Returns:
        Tuple of (PIL Image, prompt used)
    """
    from diffusers import StableDiffusionPipeline
    import torch
    
    # Create a zany prompt
    if mnemonic:
        # Extract vivid words from mnemonic
        prompt = f"Wacky, colorful cartoon illustration of: {mnemonic[:50]}. Wild colors, exaggerated, memorable, vivid."
    else:
        prompt = f"Wild, wacky, exaggerated cartoon illustration of {concept}. Bright colors, silly, memorable, vivid style."
    
    try:
        pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float32,
            safety_checker=None
        )
        pipe.to("cpu")
        
        with torch.no_grad():
            image = pipe(
                prompt,
                num_inference_steps=num_steps,
                guidance_scale=7.5,
                height=512,
                width=512
            ).images[0]
        
        return image, prompt
    except Exception as e:
        return None, f"Error: {str(e)[:50]}"

# ==================== SEMANTIC ANSWER EVALUATION ====================

def evaluate_answer_semantically(user_answer, reference_answer, card_topic):
    """
    Use Claude Haiku to evaluate if user's answer is semantically correct.
    Returns: {"status": "Correct"|"Partial"|"Incorrect", "explanation": "..."}
    
    Args:
        user_answer: What the user typed
        reference_answer: The reference fact from the card
        card_topic: The card title for context
    
    Returns:
        Dict with 'status' and 'explanation' or None if API fails
    """
    import json
    import requests
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"status": "error", "explanation": "API key not configured"}
    
    prompt = f"""You are a kind, encouraging tutor evaluating a student's answer.

Topic: {card_topic}
Reference Answer: {reference_answer}
Student's Answer: {user_answer}

Compare them for semantic accuracy. Ignore minor wording differences. Be generous—if the core concept is correct, mark it Correct.

Respond in JSON format ONLY (no preamble):
{{
  "status": "Correct" or "Partial" or "Incorrect",
  "explanation": "One sentence feedback. Be encouraging."
}}"""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 200,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
            },
            timeout=15
        )
        
        if response.status_code != 200:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("error", {}).get("message", error_detail)
            except:
                pass
            return {"status": "error", "explanation": f"API error {response.status_code}: {error_detail}"}
        
        api_response = response.json()
        text_content = api_response["content"][0]["text"].strip()
        
        # Clean up markdown if present
        if text_content.startswith("```json"):
            text_content = text_content[7:]
        if text_content.startswith("```"):
            text_content = text_content[3:]
        if text_content.endswith("```"):
            text_content = text_content[:-3]
        text_content = text_content.strip()
        
        result = json.loads(text_content)
        return result
    
    except Exception as e:
        return {"status": "error", "explanation": f"Error: {str(e)[:50]}"}

# ==================== LLM-POWERED FLASHCARD GENERATION ====================

def generate_flashcards_from_llm(raw_text, reading_level="intermediate"):
    """
    Send raw text to Claude API and get structured flashcards back as JSON.
    
    Args:
        raw_text: Raw text block to convert to flashcards
        reading_level: "simple" (ages 4-11), "intermediate" (ages 11-18), or "complex" (ages 18+)
    
    Returns:
        List of flashcard dicts with 'title', 'facts', 'emoji', 'image_prompt' keys
        or None if API call fails
    """
    import json
    import requests
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("❌ ANTHROPIC_API_KEY not set. Please add it to your environment.")
        return None
    
    # Adapt the prompt based on reading level
    if reading_level == "simple":
        level_instructions = """READING LEVEL: EASY (Ages 4-11 — Primary School)
- Use VERY simple words only. Like a children's picture book.
- Short sentences (8-12 words max per fact).
- Avoid big/technical/academic words entirely.
- If a complex word MUST be used, explain it simply in the same sentence.
- Use "kids" instead of "children", "big" instead of "significant", "start" instead of "commence", etc.
- Titles should be 2-4 simple words.
- Make it sound friendly and fun, like a teacher explaining to young kids.
- Examples of good simple facts:
  * "The moon goes around the Earth."
  * "Plants need sun and water to grow."
  * "Chimpanzees live in groups called communities."
"""
    elif reading_level == "complex":
        level_instructions = """READING LEVEL: ADVANCED (Ages 18+ — University)
- Use precise, academic language where appropriate.
- Include technical terms and proper terminology.
- Can use longer, more detailed facts (up to 25 words per fact).
- Assume the reader has strong vocabulary and background knowledge.
- Maintain accuracy and depth.
"""
    else:  # intermediate
        level_instructions = """READING LEVEL: MEDIUM (Ages 11-18 — Secondary School)
- Use clear, everyday language that a teenager would understand.
- Medium-length sentences (12-18 words per fact).
- Explain any technical terms briefly when used.
- Balance clarity with informativeness.
"""
    
    prompt = f"""You are creating flashcards for a student. Follow the reading level requirements EXACTLY.

{level_instructions}

TEXT TO CONVERT:
{raw_text}

Return ONLY a valid JSON array in this exact format (no preamble, no explanation, just JSON):
[
  {{
    "title": "Brief title/topic",
    "facts": ["Fact 1", "Fact 2", "Fact 3"],
    "topic_keyword": "main keyword for emoji matching"
  }}
]

Rules:
- Create 3-5 flashcards
- Each card has 1-3 facts
- Facts MUST match the reading level above — this is critical!
- If the reading level is Easy, even a 6-year-old should understand every word."""

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
                "messages": [
                    {"role": "user", "content": prompt}
                ],
            },
            timeout=30
        )
        
        if response.status_code != 200:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("error", {}).get("message", error_detail)
            except:
                pass
            st.error(f"❌ API Error {response.status_code}: {error_detail}")
            return None
        
        # Extract JSON from response
        api_response = response.json()
        text_content = api_response["content"][0]["text"]
        
        # Clean up response (remove markdown code blocks if present)
        text_content = text_content.strip()
        if text_content.startswith("```json"):
            text_content = text_content[7:]
        if text_content.startswith("```"):
            text_content = text_content[3:]
        if text_content.endswith("```"):
            text_content = text_content[:-3]
        text_content = text_content.strip()
        
        # Parse JSON
        flashcard_data = json.loads(text_content)
        
        # Convert to app format
        flashcards = []
        for card_data in flashcard_data:
            topic_keyword = card_data.get("topic_keyword", card_data["title"])
            topic, emoji = identify_topic(topic_keyword)
            
            flashcards.append({
                'title': card_data['title'],
                'facts': card_data['facts'],
                'emoji': emoji,
                'image_prompt': f"Illustrate: {card_data['title']}",
                'is_front': True
            })
        
        return flashcards
    
    except json.JSONDecodeError as e:
        st.error(f"❌ Failed to parse JSON response: {e}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ API request failed: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None

# ==================== SIMPLE FLASHCARD GENERATION ====================

def generate_simple_flashcards(main_concept, key_facts):
    """
    Simple, clean flashcard format: Title (front) + Facts (back)
    Optimized for accessibility and neurodiverse learners.
    
    Args:
        main_concept: Main concept/title
        key_facts: List of related facts
    
    Returns:
        List of dicts with 'title', 'facts', 'emoji', and 'image_prompt'
    """
    flashcards = []
    
    # Main concept card
    topic, emoji = identify_topic(main_concept)
    
    # First card: Main concept
    flashcards.append({
        'title': main_concept[:50],  # Keep title concise
        'facts': [main_concept],
        'emoji': emoji,
        'image_prompt': f"Illustrate: {main_concept}",
        'is_front': True
    })
    
    # Create cards from key facts
    for i, fact in enumerate(key_facts):
        topic, emoji = identify_topic(fact)
        
        # Extract a title from the fact (first 3-5 words)
        words = fact.split()
        title = ' '.join(words[:min(4, len(words))])
        
        flashcards.append({
            'title': title,
            'facts': [fact],
            'emoji': emoji,
            'image_prompt': f"Visualize: {fact[:60]}",
            'is_front': True
        })
    
    return flashcards

# ==================== DOCUMENT EXTRACTION ====================

def extract_text_from_file(uploaded_file):
    """
    Extract text from PDF, DOCX, or TXT file.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
    
    Returns:
        Extracted text as string
    """
    try:
        if uploaded_file.type == "text/plain":
            text = uploaded_file.read().decode('utf-8')
            return text
        
        elif uploaded_file.type == "application/pdf":
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
            except ImportError:
                return "PDF support needs PyPDF2. Install: pip install PyPDF2"
        
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            try:
                from docx import Document
                doc = Document(uploaded_file)
                text = "\n".join([para.text for para in doc.paragraphs])
                return text
            except ImportError:
                return "DOCX support needs python-docx. Install: pip install python-docx"
        
        else:
            return "Not supported. Use PDF, DOCX, or TXT."
    
    except Exception as e:
        return f"Error reading file: {str(e)}"

# ==================== SUMMARIZATION ====================

@st.cache_resource
def get_bart_model_and_tokenizer():
    """Load BART model and tokenizer"""
    model = BartForConditionalGeneration.from_pretrained(SUMMARIZATION_MODEL)
    tokenizer = BartTokenizer.from_pretrained(SUMMARIZATION_MODEL)
    return model, tokenizer

def summarise_text(text, reading_level="intermediate"):
    """
    Summarise text and format as learning flashcard.
    
    Args:
        text: Input text to summarise
        reading_level: 'simple', 'intermediate', or 'complex'
    
    Returns:
        Dictionary with main_concept, key_facts, and full_text
    """
    try:
        model, tokenizer = get_bart_model_and_tokenizer()
        
        # Split into sentences
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if not sentences:
            return {
                'main_concept': "Unable to process text",
                'key_facts': [],
                'full_text': text
            }
        
        # Determine summary length based on reading level
        config = {
            "simple": {"max_length": 50, "min_length": 20, "num_facts": 2},
            "intermediate": {"max_length": 100, "min_length": 40, "num_facts": 3},
            "complex": {"max_length": 150, "min_length": 60, "num_facts": 4}
        }[reading_level]
        
        # Summarize
        inputs = tokenizer(text, max_length=1024, return_tensors="pt", truncation=True)
        summary_ids = model.generate(
            inputs["input_ids"],
            max_length=config["max_length"],
            min_length=config["min_length"],
            num_beams=4,
            early_stopping=True
        )
        full_summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        
        # Extract main concept and key facts
        sentences = [s.strip() for s in full_summary.split('.') if s.strip()]
        main_concept = sentences[0].strip() if sentences else full_summary
        
        key_facts = []
        for i, sentence in enumerate(sentences[1:]):
            if i >= config["num_facts"]:
                break
            fact = sentence.strip()
            if fact:
                key_facts.append(fact)
        
        return {
            'main_concept': main_concept,
            'key_facts': key_facts,
            'full_text': full_summary
        }
    
    except Exception as e:
        return {
            'main_concept': f"Error: {str(e)}",
            'key_facts': [],
            'full_text': f"Error: {str(e)}"
        }

# ==================== SMART NOUN EXTRACTION ====================

def extract_key_nouns(text):
    """
    Extract key nouns from text for image generation.
    Filters out common words and keeps meaningful nouns/adjectives.
    
    Args:
        text: Text to extract from
    
    Returns:
        String of key nouns/phrases
    """
    # Common words to skip
    skip_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'can', 'may', 'might', 'must', 'and', 'or',
        'but', 'in', 'on', 'at', 'by', 'to', 'of', 'for', 'with', 'from',
        'about', 'that', 'this', 'these', 'those', 'as', 'he', 'she', 'it',
        'they', 'them', 'their', 'his', 'her', 'its', 'often', 'widely',
        'regarded', 'called', 'known', 'considered'
    }
    
    # Split into words and clean
    words = text.lower().split()
    
    # Extract meaningful words
    key_words = []
    for word in words:
        # Remove punctuation
        clean_word = word.strip('.,!?;:()[]{}"\'-')
        
        # Keep words that are:
        # - Not in skip list
        # - Longer than 2 characters
        # - Not numbers
        if (clean_word and 
            clean_word not in skip_words and 
            len(clean_word) > 2 and 
            not clean_word.isdigit()):
            key_words.append(clean_word)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_words = []
    for word in key_words:
        if word not in seen:
            seen.add(word)
            unique_words.append(word)
    
    # Return first 8 key words (enough to be descriptive)
    return ', '.join(unique_words[:8])

# ==================== IMAGE GENERATION ====================

@st.cache_resource
def get_diffusion_pipeline():
    """Load Stable Diffusion pipeline"""
    pipe = StableDiffusionPipeline.from_pretrained(
        IMAGE_MODEL,
        torch_dtype=torch.float32,
        safety_checker=None
    )
    pipe.enable_attention_slicing()
    return pipe

def generate_cartoon_from_reference(main_concept, num_steps=30):
    """
    Generate a cartoon version inspired by real reference images.
    Uses extracted nouns for better accuracy.
    
    Args:
        main_concept: The main concept text from summarization
        num_steps: Quality (10-30)
    
    Returns:
        Tuple: (PIL Image or error message, reference_url)
    """
    try:
        # Extract key nouns from main concept
        key_nouns = extract_key_nouns(main_concept)
        
        # Create detailed prompt using key nouns
        cartoon_prompt = (
            f"Cartoon educational illustration of {key_nouns}. "
            f"Simple, colorful, clear, kid-friendly style. "
            f"High quality illustration, easy to understand, "
            f"no text or labels. Inspired by real-world imagery."
        )
        
        pipe = get_diffusion_pipeline()
        num_steps = max(10, min(int(num_steps), 30))
        
        # Generate at 384x384 for better mobile support and faster generation
        image = pipe(
            cartoon_prompt,
            num_inference_steps=num_steps,
            guidance_scale=7.5,
            height=384,
            width=384
        ).images[0]
        
        torch.cuda.empty_cache()
        return image, None
    
    except RuntimeError as e:
        if 'out of memory' in str(e).lower():
            return "Out of memory - try reducing picture quality or turning off pictures", None
        return f"Error generating image: {str(e)}", None
    except Exception as e:
        return f"Error: {str(e)}", None

# ==================== STYLING ====================

def apply_styles(font_style, text_size, colour_scheme):
    """Apply dyslexia-friendly CSS styling using targeted Streamlit DOM selectors"""
    
    # Color schemes
    colors = {
        "Cream (Dyslexia Friendly)": {
            "bg": "#F5F1E8",
            "text": "#2C2416",
            "accent": "#8B6914"
        },
        "Soft Blue": {
            "bg": "#E8F1F5",
            "text": "#1C3A42",
            "accent": "#3A7CA5"
        },
        "Light Grey": {
            "bg": "#F1F1F1",
            "text": "#2C2C2C",
            "accent": "#666666"
        },
        "Pale Lavender": {
            "bg": "#F5E8F5",
            "text": "#3C2C42",
            "accent": "#7C3C9C"
        },
        "Pale Mint": {
            "bg": "#E8F5F1",
            "text": "#1C3C32",
            "accent": "#3C8C6C"
        },
    }
    
    selected_colors = colors.get(colour_scheme, colors["Cream (Dyslexia Friendly)"])
    
    # SOLUTION 2: Targeted Streamlit DOM selectors with !important flags (NO universal selector)
    st.markdown(f"""
    <style>
    /* ===== MAIN STREAMLIT CONTAINERS ===== */
    [data-testid="stAppViewContainer"] {{
        background-color: {selected_colors['bg']} !important;
    }}
    
    [data-testid="stMainBlockContainer"] {{
        background-color: {selected_colors['bg']} !important;
    }}
    
    section[data-testid="stSidebar"] {{
        background-color: {selected_colors['bg']} !important;
    }}
    
    [data-testid="stColumn"] {{
        background-color: {selected_colors['bg']} !important;
    }}
    
    /* ===== TEXT IN MARKDOWN CONTAINERS ONLY ===== */
    [data-testid="stMarkdownContainer"] {{
        background-color: transparent !important;
    }}
    
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stMarkdownContainer"] li {{
        font-family: {font_style}, sans-serif !important;
        font-size: {text_size}px !important;
        color: {selected_colors['text']} !important;
        letter-spacing: 0.35px !important;
        word-spacing: 1.23px !important;
        line-height: 1.8 !important;
    }}
    
    /* ===== HEADINGS ===== */
    h1, h2, h3, h4, h5, h6 {{
        font-family: {font_style}, sans-serif !important;
        color: {selected_colors['accent']} !important;
        font-weight: 700 !important;
        letter-spacing: 0.35px !important;
    }}
    
    /* ===== FORM ELEMENTS ===== */
    label {{
        font-family: {font_style}, sans-serif !important;
        font-size: {text_size}px !important;
        color: {selected_colors['text']} !important;
        background-color: transparent !important;
        letter-spacing: 0.35px !important;
    }}
    
    /* Selectbox */
    [data-testid="stSelectbox"] div div {{
        background-color: #FFFFFF !important;
        color: {selected_colors['text']} !important;
    }}
    
    /* Text Input */
    [data-testid="stTextInput"] input {{
        background-color: #FFFFFF !important;
        color: {selected_colors['text']} !important;
        font-family: {font_style}, sans-serif !important;
        font-size: {text_size}px !important;
    }}
    
    /* Text Area */
    [data-testid="stTextArea"] textarea {{
        background-color: #FFFFFF !important;
        color: {selected_colors['text']} !important;
        font-family: {font_style}, sans-serif !important;
        font-size: {text_size}px !important;
    }}
    
    /* Radio Buttons */
    [data-testid="stRadio"] label {{
        background-color: transparent !important;
        font-family: {font_style}, sans-serif !important;
        font-size: {text_size}px !important;
        color: {selected_colors['text']} !important;
    }}
    
    /* Checkboxes */
    [data-testid="stCheckbox"] label {{
        background-color: transparent !important;
        font-family: {font_style}, sans-serif !important;
        font-size: {text_size}px !important;
        color: {selected_colors['text']} !important;
    }}
    
    /* ===== BUTTONS ===== */
    button {{
        font-family: {font_style}, sans-serif !important;
        font-size: {text_size}px !important;
        transition: background-color 0.2s ease !important;
    }}
    
    button:hover {{
        background-color: rgba(0, 0, 0, 0.05) !important;
    }}
    
    /* ===== MISCELLANEOUS ===== */
    i, em {{
        font-style: normal !important;
    }}
    
    hr {{
        border-color: {selected_colors['accent']} !important;
    }}
    </style>
    """, unsafe_allow_html=True)
